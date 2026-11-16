"""Persist anomalous paid totals for administrator review.

The comparison uses the authoritative quote, including quantity, rate and
discount. A mismatch cannot be explained by those legitimate price changes.
"""
import logging
import json
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

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


def _post_webhook(url, payload):
    request = Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(request, timeout=5) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError("alert endpoint rejected notification")


def notify_pending(conn, webhook_url, *, send=_post_webhook):
    """Send each pending alert; failed deliveries remain pending for the next scan.

    Delivery is at least once: a crash after the endpoint accepts a message and
    before the database update may result in a repeat. Consumers can deduplicate
    with the stable alert_id.
    """
    parts = urlsplit(webhook_url or "")
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise ValueError("EVENTHUB_ALERT_WEBHOOK_URL must be an HTTPS URL")
    rows = conn.execute(
        "SELECT id, order_id, expected_minor, actual_minor, currency, reason "
        "FROM purchase_alerts WHERE notified_at IS NULL ORDER BY id"
    ).fetchall()
    sent = failed = 0
    for row in rows:
        payload = {"type": "eventhub.purchase_alert", "alert_id": row["id"],
                   "order_id": row["order_id"], "expected_minor": row["expected_minor"],
                   "actual_minor": row["actual_minor"], "currency": row["currency"],
                   "reason": row["reason"]}
        try:
            send(webhook_url, payload)
        except Exception:
            log.exception("Alert notification failed for alert %s", row["id"])
            failed += 1
            continue
        conn.execute("UPDATE purchase_alerts SET notified_at=? WHERE id=? AND notified_at IS NULL",
                     (database.to_iso(database.utcnow()), row["id"]))
        sent += 1
    return sent, failed
