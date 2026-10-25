import sqlite3

import pytest

from eventhub import database


def test_init_creates_tables(conn):
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "events", "exchange_rates", "orders", "audit_log"} <= names


def test_init_is_idempotent(conn):
    database.init_db(conn)


def test_transaction_commits(conn):
    with database.transaction(conn):
        conn.execute("INSERT INTO users (name,email,password_hash,created_at) VALUES ('a','a@x.io','h','t')")
    assert conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 1


def test_transaction_rolls_back_on_error(conn):
    with pytest.raises(RuntimeError):
        with database.transaction(conn):
            conn.execute("INSERT INTO users (name,email,password_hash,created_at) VALUES ('a','a@x.io','h','t')")
            raise RuntimeError("boom")
    assert conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0


def test_inventory_cannot_go_negative_at_db_level(conn):
    conn.execute("INSERT INTO events (name,artist,venue,city,starts_at,base_price_cents,capacity,tickets_available)"
                 " VALUES ('n','a','v','c','2030-01-01',100,5,5)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE events SET tickets_available = -1")


def test_role_constraint(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO users (name,email,password_hash,role,created_at) VALUES ('a','a@x.io','h','root','t')")
