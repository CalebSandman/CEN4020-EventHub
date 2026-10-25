"""EventHub Database container (SQLite).

Owns the schema, connection settings and the transaction helper. Components
receive a ``sqlite3.Connection``; none of them opens its own, which keeps every
component standalone and testable against a temporary database.

Connections run in autocommit mode (``isolation_level=None``) and transactions
are explicit via :func:`transaction`.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'buyer' CHECK (role IN ('buyer', 'admin')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    artist            TEXT NOT NULL,
    venue             TEXT NOT NULL,
    city              TEXT NOT NULL,
    starts_at         TEXT NOT NULL,
    base_price_cents  INTEGER NOT NULL CHECK (base_price_cents > 0),
    capacity          INTEGER NOT NULL CHECK (capacity > 0),
    tickets_available INTEGER NOT NULL,
    UNIQUE (name, venue, starts_at),
    CHECK (tickets_available >= 0 AND tickets_available <= capacity)
);

CREATE TABLE IF NOT EXISTS exchange_rates (
    currency   TEXT PRIMARY KEY,
    rate       TEXT NOT NULL,
    decimals   INTEGER NOT NULL CHECK (decimals BETWEEN 0 AND 4),
    updated_at TEXT NOT NULL,
    updated_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id),
    event_id          INTEGER NOT NULL REFERENCES events(id),
    quantity          INTEGER NOT NULL CHECK (quantity > 0),
    currency          TEXT NOT NULL,
    exchange_rate     TEXT NOT NULL,
    discount_percent  TEXT NOT NULL,
    total_minor       INTEGER NOT NULL CHECK (total_minor >= 0),
    currency_decimals INTEGER NOT NULL,
    created_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, id DESC);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    user_id     INTEGER,
    user_email  TEXT,
    event_ref   TEXT,
    quantity    TEXT,
    currency    TEXT,
    outcome     TEXT NOT NULL CHECK (outcome IN ('success', 'fail')),
    reason_code TEXT,
    order_id    INTEGER
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(id DESC);
"""


def utcnow() -> datetime:
    """Current time as an aware UTC datetime (single place to patch in tests)."""
    return datetime.now(timezone.utc)


def to_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def connect(path) -> sqlite3.Connection:
    """Open a connection configured for EventHub (rows as mappings, FKs on)."""
    target = str(path)
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    if target != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables (idempotent)."""
    conn.executescript(SCHEMA)


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Run a block in one write transaction (``BEGIN IMMEDIATE``).

    Commits on success; rolls back and re-raises on any exception. Taking the
    write lock up front is what makes check-then-decrement safe under
    concurrent purchases.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
