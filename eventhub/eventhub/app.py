"""Application factory: wires the components together (the "main program")."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask

from . import catalog, database, pricing
from .boundary import register_boundary

ROOT = Path(__file__).resolve().parent.parent


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("EVENTHUB_SECRET_KEY"),
        DATABASE_PATH=os.environ.get("EVENTHUB_DB", str(ROOT / "instance" / "eventhub.db")),
        EVENT_SEED_PATH=str(ROOT / "data" / "events.json"),
        RATE_SEED_PATH=str(ROOT / "data" / "exchange_rates.json"),
        CSRF_ENABLED=True,
        SESSION_LIFETIME_MINUTES=30,  # placeholder: see docs/open-questions.md
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("EVENTHUB_COOKIE_SECURE") == "1",
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if overrides:
        app.config.update(overrides)
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        logging.getLogger(__name__).warning(
            "EVENTHUB_SECRET_KEY not set: using a random key; sessions reset on restart."
        )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=app.config["SESSION_LIFETIME_MINUTES"])

    # Application setup: schema, exchange rates, then the event catalogue file.
    conn = database.connect(app.config["DATABASE_PATH"])
    try:
        database.init_db(conn)
        pricing.load_rate_seed(conn, app.config["RATE_SEED_PATH"])
        catalog.load_seed(conn, app.config["EVENT_SEED_PATH"])
    finally:
        conn.close()

    register_boundary(app)
    return app
