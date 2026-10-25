"""Purchasing & Orders component.

Coordinates the purchase path:
    identity check -> quantity -> event -> currency -> pricing ->
    inventory (atomic) -> mock payment -> order -> audit

plus checkout preview, order history and order confirmation.

Design rules (from the C4 model and Call 4):
  * the server recomputes every total; nothing price-related is trusted from the client
  * availability check + decrement is one atomic guarded UPDATE (inventory)
  * the success audit row is written in the SAME transaction as the order;
    every failure is audited after rollback, so all attempt paths are logged
  * checkout preview writes nothing, so an abandoned checkout cannot corrupt data
  * no external payment provider (ticket-purchasing-005/006)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from . import audit, catalog, database, inventory, pricing

log = logging.getLogger(__name__)

# OPEN QUESTION: "excessively large quantities" must be rejected (server-side-
# validation-004) and the purchase-limit argument is "settled" in Call 4, but the
# number is not in the written requirements. 10 is a PLACEHOLDER. See
# docs/open-questions.md (Q2).
MAX_TICKETS_PER_ORDER = 10

# Failure codes: distinct per condition (logging-and-auditing-003/004).
NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
INVALID_QUANTITY = "INVALID_QUANTITY"
EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
SOLD_OUT = "SOLD_OUT"
INSUFFICIENT_AVAILABILITY = "INSUFFICIENT_AVAILABILITY"
UNSUPPORTED_CURRENCY = "UNSUPPORTED_CURRENCY"
PAYMENT_DECLINED = "PAYMENT_DECLINED"
INTERNAL_ERROR = "INTERNAL_ERROR"

_INT_RE = re.compile(r"[+-]?\d{1,18}")


class PurchaseError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CheckoutPreview:
    event: catalog.Event
    quantity: int
    currency: str
    quote: pricing.PriceQuote
    discount_eligible: bool


@dataclass(frozen=True)
class Order:
    id: int
    user_id: int
    event_id: int
    event_name: str
    artist: str
    venue: str
    starts_at: str
    quantity: int
    currency: str
    exchange_rate: Decimal
    discount_percent: Decimal
    total_minor: int
    currency_decimals: int
    created_at: str

    @property
    def total_display(self) -> str:
        return pricing.format_money(self.total_minor, self.currency, self.currency_decimals)


def mock_payment(user, amount_minor: int, currency: str) -> bool:
    """Pretend payment: always approves. No external provider is ever contacted."""
    return True


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_quantity(raw) -> int:
    """Server-side quantity validation: whole number, 1..MAX_TICKETS_PER_ORDER."""
    if isinstance(raw, bool):
        raise PurchaseError(INVALID_QUANTITY, "Ticket quantity must be a whole number.")
    if isinstance(raw, int):
        value = raw
    else:
        text = str(raw if raw is not None else "").strip()
        if not _INT_RE.fullmatch(text):
            raise PurchaseError(INVALID_QUANTITY, "Ticket quantity must be a whole number.")
        value = int(text)
    if value == 0:
        raise PurchaseError(INVALID_QUANTITY, "Ticket quantity cannot be zero.")
    if value < 0:
        raise PurchaseError(INVALID_QUANTITY, "Ticket quantity cannot be negative.")
    if value > MAX_TICKETS_PER_ORDER:
        raise PurchaseError(
            INVALID_QUANTITY, f"You can buy at most {MAX_TICKETS_PER_ORDER} tickets per order."
        )
    return value


def _prepare(conn, user, event_id, quantity_raw, currency_raw):
    """Run every pre-purchase check in the order of ticket-purchasing-010."""
    if user is None:
        raise PurchaseError(NOT_AUTHENTICATED, "You must be logged in to buy tickets.")
    quantity = validate_quantity(quantity_raw)
    event = catalog.get_event(conn, event_id)
    if event is None:
        raise PurchaseError(EVENT_NOT_FOUND, "That event does not exist.")
    if event.sold_out:
        raise PurchaseError(SOLD_OUT, "Sorry, this event is sold out.")
    currency = pricing.normalize_currency(currency_raw)
    if currency not in pricing.supported_currencies(conn):
        raise PurchaseError(UNSUPPORTED_CURRENCY, "That currency is not supported.")
    if quantity > event.tickets_available:
        raise PurchaseError(
            INSUFFICIENT_AVAILABILITY,
            f"Only {event.tickets_available} ticket(s) remain for this event.",
        )
    eligible = pricing.is_discount_eligible(user.email)
    quote = pricing.calculate_price(conn, event.base_price_cents, quantity, eligible, currency)
    return event, quantity, currency, quote, eligible


def _log_failure(conn, user, event_id, quantity_raw, currency_raw, code, now=None) -> None:
    audit.record(conn, user_id=user.id if user else None, user_email=user.email if user else None,
                 event_ref=event_id, quantity=quantity_raw, currency=currency_raw,
                 outcome=audit.OUTCOME_FAIL, reason_code=code, now=now)


def preview_checkout(conn, user, event_id, quantity_raw, currency_raw) -> CheckoutPreview:
    """Quote for the checkout page. Holds no tickets and creates no order.

    A *successful* preview writes nothing (it is not a purchase). A *rejected*
    one is a failed purchase attempt - the buyer pressed Checkout and was
    refused - so it is audited like any other failure.
    """
    try:
        event, quantity, currency, quote, eligible = _prepare(
            conn, user, event_id, quantity_raw, currency_raw)
    except PurchaseError as exc:
        _log_failure(conn, user, event_id, quantity_raw, currency_raw, exc.code)
        raise
    return CheckoutPreview(event, quantity, currency, quote, eligible)


def record_unauthenticated_attempt(conn, event_id, quantity_raw, currency_raw) -> None:
    _log_failure(conn, None, event_id, quantity_raw, currency_raw, NOT_AUTHENTICATED)


# --------------------------------------------------------------------------- #
# Purchase
# --------------------------------------------------------------------------- #
def purchase(conn, user, event_id, quantity_raw, currency_raw, *,
             payment=mock_payment, now: datetime | None = None) -> Order:
    """Complete a purchase or raise :class:`PurchaseError`. Always audited."""
    def log_failure(code: str) -> None:
        _log_failure(conn, user, event_id, quantity_raw, currency_raw, code, now)

    try:
        event, quantity, currency, quote, _ = _prepare(conn, user, event_id, quantity_raw, currency_raw)
        with database.transaction(conn):
            if not inventory.reserve(conn, event.id, quantity):
                left = inventory.available(conn, event.id) or 0
                if left == 0:
                    raise PurchaseError(SOLD_OUT, "Sorry, this event is sold out.")
                raise PurchaseError(
                    INSUFFICIENT_AVAILABILITY,
                    f"Tickets became unavailable. Only {left} ticket(s) remain.",
                )
            if not payment(user, quote.total_minor, currency):
                raise PurchaseError(PAYMENT_DECLINED, "The payment was declined.")
            stamp = database.to_iso(now or database.utcnow())
            cur = conn.execute(
                "INSERT INTO orders (user_id, event_id, quantity, currency, exchange_rate, "
                "discount_percent, total_minor, currency_decimals, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (user.id, event.id, quantity, currency, format(quote.exchange_rate, "f"),
                 format(quote.discount_percent, "f"), quote.total_minor, quote.decimals, stamp),
            )
            order_id = cur.lastrowid
            audit.record(conn, user_id=user.id, user_email=user.email, event_ref=event_id,
                         quantity=quantity, currency=currency, outcome=audit.OUTCOME_SUCCESS,
                         order_id=order_id, now=now)
    except PurchaseError as exc:
        log_failure(exc.code)
        raise
    except Exception:
        log.exception("unexpected error during purchase")
        log_failure(INTERNAL_ERROR)
        raise PurchaseError(INTERNAL_ERROR, "Something went wrong. You were not charged.") from None
    return get_order(conn, user, order_id)


# --------------------------------------------------------------------------- #
# Orders (history + confirmation)
# --------------------------------------------------------------------------- #
_ORDER_SELECT = (
    "SELECT o.id, o.user_id, o.event_id, e.name AS event_name, e.artist, e.venue, e.starts_at, "
    "o.quantity, o.currency, o.exchange_rate, o.discount_percent, o.total_minor, "
    "o.currency_decimals, o.created_at FROM orders o JOIN events e ON e.id = o.event_id "
)


def _row_to_order(row) -> Order:
    data = {k: row[k] for k in row.keys()}
    data["exchange_rate"] = Decimal(data["exchange_rate"])
    data["discount_percent"] = Decimal(data["discount_percent"])
    return Order(**data)


def _require_user(user):
    if user is None:
        raise PurchaseError(NOT_AUTHENTICATED, "You must be logged in to view orders.")


def list_orders(conn, user) -> list[Order]:
    """The user's own orders, newest first."""
    _require_user(user)
    rows = conn.execute(_ORDER_SELECT + "WHERE o.user_id = ? ORDER BY o.id DESC", (user.id,))
    return [_row_to_order(r) for r in rows.fetchall()]


def get_order(conn, user, order_id) -> Order | None:
    """One of the user's own orders (others' orders look like 'not found')."""
    _require_user(user)
    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return None
    if not 1 <= order_id <= 2**63 - 1:
        return None
    row = conn.execute(_ORDER_SELECT + "WHERE o.id = ? AND o.user_id = ?", (order_id, user.id)).fetchone()
    return _row_to_order(row) if row else None
