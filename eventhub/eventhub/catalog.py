"""Event Catalog component.

Browse, search by artist or venue, event detail lookups, the no-match fallback
and the one-time import of the setup data file. Read-only with respect to
inventory (writes to ticket counts belong to the Inventory component).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

SEARCH_FIELDS = ("artist", "venue")
NO_MATCH_MESSAGE = "No matching events were found. Showing all events instead."
MAX_SEARCH_LENGTH = 100


@dataclass(frozen=True)
class Event:
    id: int
    name: str
    artist: str
    venue: str
    city: str
    starts_at: str
    base_price_cents: int  # list price in USD minor units
    capacity: int
    tickets_available: int

    @property
    def sold_out(self) -> bool:
        return self.tickets_available <= 0


@dataclass(frozen=True)
class SearchResult:
    events: list
    field: str
    query: str
    no_match: bool = False
    message: str | None = None


_COLUMNS = ("id, name, artist, venue, city, starts_at, base_price_cents, capacity, "
            "tickets_available")


def _row_to_event(row) -> Event:
    return Event(**{k: row[k] for k in row.keys()})


def list_events(conn) -> list[Event]:
    rows = conn.execute(f"SELECT {_COLUMNS} FROM events ORDER BY starts_at, id").fetchall()
    return [_row_to_event(r) for r in rows]


def get_event(conn, event_id) -> Event | None:
    try:
        event_id = int(event_id)
    except (TypeError, ValueError):
        return None
    if not 1 <= event_id <= 2**63 - 1:
        return None
    row = conn.execute(f"SELECT {_COLUMNS} FROM events WHERE id = ?", (event_id,)).fetchone()
    return _row_to_event(row) if row else None


def _like_pattern(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search(conn, field: str, text) -> SearchResult:
    """Search by ``artist`` or ``venue`` (case-insensitive substring).

    Blank text returns everything. If nothing matches, the result carries the
    no-match message *and* the full event list (event-browsing-009/010).
    """
    if field not in SEARCH_FIELDS:
        raise ValueError(f"field must be one of {SEARCH_FIELDS}")
    text = str(text or "").strip()[:MAX_SEARCH_LENGTH]
    if not text:
        return SearchResult(list_events(conn), field, "")
    # ``field`` is whitelisted above, so interpolating the column name is safe.
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM events WHERE {field} LIKE ? ESCAPE '\\' ORDER BY starts_at, id",
        (_like_pattern(text),),
    ).fetchall()
    if rows:
        return SearchResult([_row_to_event(r) for r in rows], field, text)
    return SearchResult(list_events(conn), field, text, True, NO_MATCH_MESSAGE)


# --------------------------------------------------------------------------- #
# Event Setup Data import
# --------------------------------------------------------------------------- #
def _usd_to_cents(value) -> int:
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"invalid price: {value!r}") from None
    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"price must be positive: {value!r}")
    return int((amount * 100).quantize(Decimal("1")))


def load_seed(conn, path) -> int:
    """Import events from the setup data file. Idempotent; returns rows added.

    Existing events (same name+venue+start) are left untouched so live
    inventory is never reset by a restart.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    added = 0
    for item in data["events"]:
        capacity = int(item["capacity"])
        if capacity <= 0:
            raise ValueError(f"capacity must be positive for {item.get('name')!r}")
        cur = conn.execute(
            "INSERT OR IGNORE INTO events (name, artist, venue, city, starts_at, "
            "base_price_cents, capacity, tickets_available) VALUES (?,?,?,?,?,?,?,?)",
            (item["name"], item["artist"], item["venue"], item["city"], item["starts_at"],
             _usd_to_cents(item["base_price_usd"]), capacity, capacity),
        )
        added += cur.rowcount
    return added
