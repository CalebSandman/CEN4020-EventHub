"""Shared fixtures. Every component test gets its own temporary database."""
from pathlib import Path

import pytest

from eventhub import catalog, database, identity, pricing
from eventhub.app import create_app

ROOT = Path(__file__).resolve().parent.parent
EVENT_SEED = ROOT / "data" / "events.json"
RATE_SEED = ROOT / "data" / "exchange_rates.json"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def conn(db_path):
    c = database.connect(db_path)
    database.init_db(c)
    yield c
    c.close()


@pytest.fixture
def seeded(conn):
    pricing.load_rate_seed(conn, RATE_SEED)
    catalog.load_seed(conn, EVENT_SEED)
    return conn


@pytest.fixture
def buyer(seeded):
    return identity.register_user(seeded, "Bea Buyer", "bea@example.com", "correct-horse-battery")


@pytest.fixture
def student(seeded):
    return identity.register_user(seeded, "Stu Dent", "Stu@USF.edu", "correct-horse-battery")


@pytest.fixture
def admin(seeded):
    return identity.create_admin_user(seeded, "Ada Admin", "ada@example.com", "admin-password-1")


def make_event(conn, name="Test Show", capacity=5, price_cents=10000, artist="Test Artist",
               venue="Test Venue"):
    cur = conn.execute(
        "INSERT INTO events (name, artist, venue, city, starts_at, base_price_cents, capacity, "
        "tickets_available) VALUES (?,?,?,?,?,?,?,?)",
        (name, artist, venue, "Testville", "2030-01-01T20:00", price_cents, capacity, capacity),
    )
    return cur.lastrowid


@pytest.fixture
def app(db_path):
    return create_app({"TESTING": True, "DATABASE_PATH": str(db_path), "SECRET_KEY": "test-secret"})


@pytest.fixture
def client(app):
    return app.test_client()


class Web:
    """Small helper that handles CSRF tokens and login for route tests."""

    def __init__(self, client):
        self.client = client

    def _arm_csrf(self):
        # Login rotates the session (and its CSRF token), like a fresh page load would.
        with self.client.session_transaction() as s:
            s["_csrf"] = "test-token"

    def post(self, url, data=None, **kw):
        self._arm_csrf()
        payload = dict(data or {})
        payload.setdefault("csrf_token", "test-token")
        return self.client.post(url, data=payload, **kw)

    def get(self, url, **kw):
        return self.client.get(url, **kw)

    def login(self, email, password):
        return self.post("/login", {"email": email, "password": password})


@pytest.fixture
def web(client):
    return Web(client)
