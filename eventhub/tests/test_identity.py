from datetime import datetime, timedelta, timezone

import pytest

from eventhub import identity
from eventhub.identity import IdentityError


def test_register_creates_buyer_with_hashed_password(conn):
    user = identity.register_user(conn, " Bea ", " Bea@Example.COM ", "longenough1")
    assert (user.name, user.email, user.role) == ("Bea", "bea@example.com", "buyer")
    stored = conn.execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored != "longenough1" and "longenough1" not in stored  # auth-006


@pytest.mark.parametrize("name,email,password,code", [
    ("", "a@b.co", "longenough1", "NAME_REQUIRED"),
    ("A", "", "longenough1", "EMAIL_REQUIRED"),
    ("A", "not-an-email", "longenough1", "EMAIL_INVALID"),
    ("A", "a@b.co", "", "PASSWORD_REQUIRED"),
    ("A", "a@b.co", "short", "PASSWORD_TOO_SHORT"),
    ("A", "a@b.co", "x" * 129, "PASSWORD_TOO_LONG"),
    ("A" * 101, "a@b.co", "longenough1", "NAME_TOO_LONG"),
])
def test_registration_requires_valid_name_email_password(conn, name, email, password, code):
    with pytest.raises(IdentityError) as err:
        identity.register_user(conn, name, email, password)
    assert err.value.code == code


def test_duplicate_email_rejected_case_insensitively(conn):
    identity.register_user(conn, "A", "a@b.co", "longenough1")
    with pytest.raises(IdentityError) as err:
        identity.register_user(conn, "B", "A@B.CO", "longenough1")
    assert err.value.code == "EMAIL_TAKEN"


def test_authenticate(conn):
    identity.register_user(conn, "A", "a@b.co", "longenough1")
    assert identity.authenticate(conn, "A@b.co", "longenough1").email == "a@b.co"
    assert identity.authenticate(conn, "a@b.co", "wrong-password") is None
    assert identity.authenticate(conn, "nobody@b.co", "longenough1") is None
    assert identity.authenticate(conn, "a@b.co", None) is None
    assert identity.authenticate(conn, "a@b.co", "x" * 5000) is None


def test_two_roles_only(conn):
    assert identity.ROLES == ("buyer", "admin")
    admin = identity.create_admin_user(conn, "Ada", "ada@b.co", "longenough1")
    assert admin.is_admin and identity.has_role(admin, "admin")
    buyer = identity.register_user(conn, "B", "b@b.co", "longenough1")
    assert not identity.has_role(buyer, "admin") and not identity.has_role(None, "buyer")


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_session_valid_then_expires_after_inactivity(conn):
    user = identity.register_user(conn, "A", "a@b.co", "longenough1")
    session = {}
    identity.start_session(session, user, now=NOW)
    assert identity.load_session_user(conn, session, now=NOW + timedelta(minutes=29)).id == user.id
    # sliding window: activity at +29 renewed it, so +58 is still within 30 min of last activity
    assert identity.load_session_user(conn, session, now=NOW + timedelta(minutes=58)) is not None
    assert identity.load_session_user(conn, session, now=NOW + timedelta(minutes=120)) is None
    assert "uid" not in session  # system-002


def test_session_with_unknown_or_garbage_data_is_rejected(conn):
    assert identity.load_session_user(conn, {}) is None
    assert identity.load_session_user(conn, {"uid": 999, "last_seen": NOW.timestamp()}, now=NOW) is None
    assert identity.load_session_user(conn, {"uid": 1, "last_seen": "junk"}, now=NOW) is None


def test_role_change_applies_immediately(conn):
    user = identity.register_user(conn, "A", "a@b.co", "longenough1")
    session = {}
    identity.start_session(session, user, now=NOW)
    conn.execute("UPDATE users SET role='admin'")
    assert identity.load_session_user(conn, session, now=NOW).role == "admin"


@pytest.mark.parametrize("target,expected", [
    ("/orders", "/orders"),
    ("/events/3/checkout?quantity=2&currency=EUR", "/events/3/checkout?quantity=2&currency=EUR"),
    ("https://evil.example/x", "/"),
    ("//evil.example/x", "/"),
    ("/\\evil.example", "/"),
    ("javascript:alert(1)", "/"),
    ("orders", "/"),
    ("", "/"),
    (None, "/"),
    ("/ok\r\nSet-Cookie: x=1", "/"),
])
def test_safe_next_url(target, expected):
    assert identity.safe_next_url(target) == expected
