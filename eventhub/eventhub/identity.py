"""Identity & Authorization component.

Registration, password hashing, login, buyer/administrator roles, session
policy (expiry), safe post-login return URLs and Flask route guards.

Everything except the guards is framework-free and takes a database connection
and a plain mapping as "session", so it unit-tests without Flask.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlsplit

from werkzeug.security import check_password_hash, generate_password_hash

from . import database

ROLE_BUYER = "buyer"
ROLE_ADMIN = "admin"
ROLES = (ROLE_BUYER, ROLE_ADMIN)  # system: exactly two roles (auth-008)

LOGIN_ENDPOINT = "auth.login"

# OPEN QUESTION: system-002 says sessions expire "after some time" but gives no
# duration. 30 minutes of inactivity is a placeholder; see docs/open-questions.md.
SESSION_LIFETIME = timedelta(minutes=30)
SESSION_USER_KEY = "uid"
SESSION_SEEN_KEY = "last_seen"

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128  # bounds hashing cost
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 254
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class IdentityError(Exception):
    """A registration/login problem with a machine code and a user message."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


# --------------------------------------------------------------------------- #
# Accounts
# --------------------------------------------------------------------------- #
def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _validate_registration(name, email, password) -> tuple[str, str]:
    name = str(name or "").strip()
    email = normalize_email(email)
    if not name:
        raise IdentityError("NAME_REQUIRED", "Name is required.")
    if len(name) > MAX_NAME_LENGTH:
        raise IdentityError("NAME_TOO_LONG", f"Name must be at most {MAX_NAME_LENGTH} characters.")
    if not email:
        raise IdentityError("EMAIL_REQUIRED", "Email is required.")
    if len(email) > MAX_EMAIL_LENGTH or not _EMAIL_RE.match(email):
        raise IdentityError("EMAIL_INVALID", "Enter a valid email address.")
    if not isinstance(password, str) or not password:
        raise IdentityError("PASSWORD_REQUIRED", "Password is required.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise IdentityError(
            "PASSWORD_TOO_SHORT", f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise IdentityError(
            "PASSWORD_TOO_LONG", f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        )
    return name, email


def _insert_user(conn, name, email, password, role) -> User:
    name, email = _validate_registration(name, email, password)
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?,?,?,?,?)",
            (name, email, generate_password_hash(password), role, database.to_iso(database.utcnow())),
        )
    except sqlite3.IntegrityError:
        raise IdentityError("EMAIL_TAKEN", "An account with that email already exists.") from None
    return User(cur.lastrowid, name, email, role)


def register_user(conn, name, email, password) -> User:
    """Public registration. Always creates a *buyer*; there is no role argument."""
    return _insert_user(conn, name, email, password, ROLE_BUYER)


def create_admin_user(conn, name, email, password) -> User:
    """Create an administrator. Used only by the management CLI, never by a route."""
    return _insert_user(conn, name, email, password, ROLE_ADMIN)


def _row_to_user(row) -> User:
    return User(row["id"], row["name"], row["email"], row["role"])


def get_user(conn, user_id) -> User | None:
    row = conn.execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


_DUMMY_HASH = generate_password_hash("not-a-real-password")


def authenticate(conn, email, password) -> User | None:
    """Return the user for valid credentials, else None (same work either way)."""
    row = conn.execute(
        "SELECT id, name, email, role, password_hash FROM users WHERE email = ?",
        (normalize_email(email),),
    ).fetchone()
    candidate = password if isinstance(password, str) else ""
    if len(candidate) > MAX_PASSWORD_LENGTH:
        candidate = ""
    if row is None:
        check_password_hash(_DUMMY_HASH, candidate)
        return None
    if check_password_hash(row["password_hash"], candidate):
        return _row_to_user(row)
    return None


# --------------------------------------------------------------------------- #
# Roles
# --------------------------------------------------------------------------- #
def has_role(user: User | None, role: str) -> bool:
    return user is not None and user.role == role


# --------------------------------------------------------------------------- #
# Session policy
# --------------------------------------------------------------------------- #
def start_session(session, user: User, now: datetime | None = None) -> None:
    now = now or database.utcnow()
    session[SESSION_USER_KEY] = user.id
    session[SESSION_SEEN_KEY] = now.timestamp()


def end_session(session) -> None:
    session.pop(SESSION_USER_KEY, None)
    session.pop(SESSION_SEEN_KEY, None)


def load_session_user(conn, session, now: datetime | None = None,
                      lifetime: timedelta = SESSION_LIFETIME) -> User | None:
    """Resolve the logged-in user, enforcing inactivity expiry (sliding window).

    The role is re-read from the database on every call, so a role change
    takes effect immediately.
    """
    uid = session.get(SESSION_USER_KEY)
    seen = session.get(SESSION_SEEN_KEY)
    if uid is None or seen is None:
        return None
    now = now or database.utcnow()
    try:
        age = now.timestamp() - float(seen)
    except (TypeError, ValueError):
        end_session(session)
        return None
    if age > lifetime.total_seconds() or age < -60:
        end_session(session)
        return None
    user = get_user(conn, uid)
    if user is None:
        end_session(session)
        return None
    session[SESSION_SEEN_KEY] = now.timestamp()
    return user


# --------------------------------------------------------------------------- #
# Safe return URL
# --------------------------------------------------------------------------- #
def safe_next_url(target, default: str = "/") -> str:
    """Return ``target`` only if it is a same-site relative path (no open redirect)."""
    if not isinstance(target, str) or not target or len(target) > 2000:
        return default
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in target):
        return default
    if not target.startswith("/") or target.startswith("//") or "\\" in target:
        return default
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return default
    return target


# --------------------------------------------------------------------------- #
# Flask route guards (Flask imported lazily so the rest stays framework-free)
# --------------------------------------------------------------------------- #
def _requested_path() -> str:
    from flask import request

    if request.method == "GET":
        path = request.full_path
        return path[:-1] if path.endswith("?") else path
    return "/"


def _login_redirect():
    from flask import redirect, url_for

    return redirect(url_for(LOGIN_ENDPOINT, next=_requested_path()))


def login_required(view):
    """Redirect unauthenticated users to login, remembering the requested page."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        from flask import g

        if getattr(g, "user", None) is None:
            return _login_redirect()
        return view(*args, **kwargs)

    return wrapper


def role_required(role: str):
    """Allow only users holding ``role``; others get 403 (unauthenticated: login)."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            from flask import abort, g

            user = getattr(g, "user", None)
            if user is None:
                return _login_redirect()
            if not has_role(user, role):
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator

