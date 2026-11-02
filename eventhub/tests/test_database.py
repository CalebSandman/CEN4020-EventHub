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


def test_existing_users_gain_home_currency_without_losing_data(db_path):
    old = sqlite3.connect(db_path)
    old.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, "
                "password_hash TEXT, role TEXT, created_at TEXT)")
    old.execute("INSERT INTO users VALUES (1,'Legacy','legacy@example.com','hash','buyer','t')")
    old.commit()
    old.close()
    upgraded = database.connect(db_path)
    try:
        database.init_db(upgraded)
        row = upgraded.execute("SELECT email, home_currency FROM users WHERE id=1").fetchone()
        assert (row["email"], row["home_currency"]) == ("legacy@example.com", "USD")
        database.init_db(upgraded)
    finally:
        upgraded.close()
