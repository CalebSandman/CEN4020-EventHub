"""Persist anomalous paid totals for administrator review.

The comparison uses the authoritative quote, including quantity, rate and
discount. A mismatch cannot be explained by those legitimate price changes.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

from . import database

DEFAULT_MIN_RATIO = Decimal("0.50")
DEFAULT_MAX_RATIO = Decimal("1.50")
log = logging.getLogger(__name__)


def record_if_suspicious(conn, order_id, expected_minor, actual_minor, currency, *,
                         min_ratio=DEFAULT_MIN_RATIO, max_ratio=DEFAULT_MAX_RATIO):
    if expected_minor <= 0:
        return False
    ratio = Decimal(actual_minor) / Decimal(expected_minor)
    if min_ratio <= ratio <= max_ratio:
        return False
    cur = conn.execute(
        "INSERT OR IGNORE INTO purchase_alerts "
        "(occurred_at, order_id, expected_minor, actual_minor, currency, reason) "
        "VALUES (?,?,?,?,?,?)",
        (database.to_iso(database.utcnow()), order_id, expected_minor, actual_minor,
         currency, "TOTAL_OUTSIDE_EXPECTED_RANGE"),
    )
    if cur.rowcount == 1:
        log.warning("Suspicious purchase total: order=%s expected_minor=%s actual_minor=%s currency=%s",
                    order_id, expected_minor, actual_minor, currency)
    return cur.rowcount == 1


def scan_orders(conn, *, min_ratio=DEFAULT_MIN_RATIO, max_ratio=DEFAULT_MAX_RATIO):
    """Reconcile stored totals with each order's historical price and rate."""
    rows = conn.execute(
        "SELECT id, base_price_cents, quantity, exchange_rate, discount_percent, "
        "currency_decimals, total_minor, currency FROM orders WHERE base_price_cents IS NOT NULL"
    ).fetchall()
    found = 0
    for row in rows:
        expected_major = (Decimal(row["base_price_cents"]) / 100 * row["quantity"]
                          * (1 - Decimal(row["discount_percent"]) / 100)
                          * Decimal(row["exchange_rate"]))
        scale = Decimal(10) ** row["currency_decimals"]
        expected = int((expected_major * scale).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        found += record_if_suspicious(conn, row["id"], expected, row["total_minor"],
                                      row["currency"], min_ratio=min_ratio, max_ratio=max_ratio)
    return found
