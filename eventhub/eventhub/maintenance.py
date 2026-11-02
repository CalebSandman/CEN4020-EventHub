"""Operator maintenance: inspect events, change ticket counts, reset sales.

Used by ``manage.py`` only (never by a web route). These functions deliberately
bypass the purchase path, so they leave no audit rows and are for administrators
with shell access to the server.
"""
from __future__ import annotations

from . import database


class MaintenanceError(Exception):
    pass


def list_events(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, tickets_available, capacity FROM events ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def set_tickets(conn, event_id: int, available: int, capacity: int | None = None) -> None:
    """Set tickets remaining (and optionally the fixed capacity) for one event."""
    row = conn.execute("SELECT capacity FROM events WHERE id = ?", (event_id,)).fetchone()
    if row is None:
        raise MaintenanceError(f"No event with id {event_id}.")
    new_capacity = row["capacity"] if capacity is None else capacity
    if new_capacity < 1:
        raise MaintenanceError("Capacity must be at least 1.")
    if not 0 <= available <= new_capacity:
        raise MaintenanceError(f"Available must be between 0 and capacity ({new_capacity}).")
    conn.execute("UPDATE events SET capacity = ?, tickets_available = ? WHERE id = ?",
                 (new_capacity, available, event_id))


def reset_sales(conn) -> dict:
    """Delete all orders and audit records and restore every event to full capacity.

    Users, administrators and exchange rates are kept.
    """
    with database.transaction(conn):
        orders = conn.execute("DELETE FROM orders").rowcount
        audits = conn.execute("DELETE FROM audit_log").rowcount
        conn.execute("UPDATE events SET tickets_available = capacity")
    return {"orders_deleted": orders, "audit_records_deleted": audits}
