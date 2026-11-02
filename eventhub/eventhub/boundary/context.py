"""Request-scoped helpers shared by all blueprints."""
from __future__ import annotations

import secrets

from flask import current_app, g, session

from .. import database, pricing

CSRF_KEY = "_csrf"
CURRENCY_KEY = "currency"


def get_db():
    if "db" not in g:
        g.db = database.connect(current_app.config["DATABASE_PATH"])
    return g.db


def csrf_token() -> str:
    token = session.get(CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_KEY] = token
    return token


def session_currency(conn) -> str:
    """The buyer's chosen display currency (validated; falls back to USD)."""
    code = pricing.normalize_currency(session.get(CURRENCY_KEY, pricing.BASE_CURRENCY))
    return code if code in pricing.supported_currencies(conn) else pricing.BASE_CURRENCY
