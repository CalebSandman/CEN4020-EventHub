"""Inventory Repository component.

The only code that changes ticket counts. ``reserve`` is a single guarded
UPDATE, so "is there enough?" and "take them" are one atomic operation.
Call it inside ``database.transaction`` together with the order insert.
"""
from __future__ import annotations


def available(conn, event_id) -> int | None:
    """Tickets left, or None if the event does not exist."""
    row = conn.execute("SELECT tickets_available FROM events WHERE id = ?", (event_id,)).fetchone()
    return None if row is None else row["tickets_available"]


def reserve(conn, event_id, quantity: int) -> bool:
    """Atomically decrement availability. False if there are not enough tickets."""
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise ValueError("quantity must be a positive integer")
    cur = conn.execute(
        "UPDATE events SET tickets_available = tickets_available - ? "
        "WHERE id = ? AND tickets_available >= ?",
        (quantity, event_id, quantity),
    )
    return cur.rowcount == 1
