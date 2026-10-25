"""Administration component (service layer).

Authorised exchange-rate editing and audit-log review. Every function takes the
acting user and re-verifies the administrator role itself, so the check holds
even if a route forgets its guard (defence in depth; C4: "verifies admin role
on every request"). The Flask adapter lives in ``boundary/admin_routes.py``;
buyer flows never import this module.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from . import audit, database, identity, pricing

MAX_RATE = Decimal("1000000")
MAX_RATE_DECIMAL_PLACES = 8


class PermissionDenied(Exception):
    pass


class AdminError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _require_admin(actor) -> None:
    if not identity.has_role(actor, identity.ROLE_ADMIN):
        raise PermissionDenied("administrator role required")


def list_rates(conn, actor) -> list[dict]:
    _require_admin(actor)
    rows = conn.execute(
        "SELECT currency, rate, decimals, updated_at, updated_by FROM exchange_rates ORDER BY currency"
    ).fetchall()
    return [dict(r) for r in rows]


def parse_rate(raw) -> Decimal:
    text = str(raw if raw is not None else "").strip()
    if not text or len(text) > 32:
        raise AdminError("RATE_INVALID", "Enter an exchange rate.")
    try:
        rate = Decimal(text)
    except InvalidOperation:
        raise AdminError("RATE_INVALID", "Exchange rate must be a number.") from None
    if not rate.is_finite() or rate <= 0:
        raise AdminError("RATE_INVALID", "Exchange rate must be greater than zero.")
    if rate > MAX_RATE:
        raise AdminError("RATE_INVALID", "Exchange rate is unrealistically large.")
    if rate.as_tuple().exponent < -MAX_RATE_DECIMAL_PLACES:
        raise AdminError("RATE_INVALID", f"At most {MAX_RATE_DECIMAL_PLACES} decimal places.")
    return rate


def update_rate(conn, actor, currency, new_rate_raw, now: datetime | None = None) -> None:
    """Change one stored rate (units of currency per 1 USD)."""
    _require_admin(actor)
    code = pricing.normalize_currency(currency)
    if code == pricing.BASE_CURRENCY:
        raise AdminError("BASE_CURRENCY", "The USD rate is fixed at 1 and cannot be changed.")
    rate = parse_rate(new_rate_raw)
    cur = conn.execute(
        "UPDATE exchange_rates SET rate = ?, updated_at = ?, updated_by = ? WHERE currency = ?",
        (format(rate, "f"), database.to_iso(now or database.utcnow()), actor.id, code),
    )
    if cur.rowcount != 1:
        raise AdminError("UNSUPPORTED_CURRENCY", "That currency is not supported.")


def review_audit(conn, actor, *, outcome=None, user_email=None, reason_code=None, limit=100):
    """Audit records for complaint investigation, read through the audit interface."""
    _require_admin(actor)
    return audit.query(conn, outcome=outcome or None, user_email=user_email or None,
                       reason_code=reason_code or None, limit=limit)
