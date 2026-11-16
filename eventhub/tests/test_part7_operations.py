"""Recovery and alert delivery follow-up from the Call 6 transcript."""
import sqlite3
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import make_event
from eventhub import alerts, database, recovery, purchasing


def test_online_backup_is_verified_and_never_overwrites(seeded, db_path, buyer, tmp_path):
    event_id = make_event(seeded, price_cents=3000)
    purchasing.purchase(seeded, buyer, event_id, 1, "JPY")
    destination = tmp_path / "verified.db"
    counts = recovery.backup_database(db_path, destination)
    assert counts["orders"] == 1
    assert counts == recovery.verify_backup(destination)
    assert destination.stat().st_size > 0
    with pytest.raises(FileExistsError):
        recovery.backup_database(db_path, destination)
    assert recovery.verify_backup(db_path)["orders"] == 1


def test_backup_verification_rejects_corrupt_and_missing_files(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(ValueError):
        recovery.verify_backup(missing)
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a SQLite database")
    with pytest.raises(sqlite3.DatabaseError):
        recovery.verify_backup(corrupt)


def test_backup_cli_creates_and_verifies_copy(seeded, db_path, tmp_path):
    root = Path(__file__).resolve().parents[1]
    destination = tmp_path / "cli-backup.db"
    env = dict(os.environ, EVENTHUB_DB=str(db_path))
    backup = subprocess.run(
        [sys.executable, str(root / "manage.py"), "backup-db", str(destination)],
        cwd=root, env=env, capture_output=True, text=True,
    )
    assert backup.returncode == 0, backup.stderr + backup.stdout
    verify = subprocess.run(
        [sys.executable, str(root / "manage.py"), "verify-backup", str(destination)],
        cwd=root, env=env, capture_output=True, text=True,
    )
    assert verify.returncode == 0 and "Backup verified" in verify.stdout


def test_alert_notification_retries_failed_delivery_and_deduplicates(seeded, buyer):
    event_id = make_event(seeded, price_cents=3000)
    order = purchasing.purchase(seeded, buyer, event_id, 1, "JPY")
    seeded.execute("UPDATE orders SET total_minor=45 WHERE id=?", (order.id,))
    assert alerts.scan_orders(seeded) == 1
    assert alerts.scan_orders(seeded) == 0
    delivered = []

    def fail_once(_url, payload):
        delivered.append(payload)
        if len(delivered) == 1:
            raise OSError("temporarily unavailable")

    endpoint = "https://alerts.example.test/eventhub"
    assert alerts.notify_pending(seeded, endpoint, send=fail_once) == (0, 1)
    assert alerts.notify_pending(seeded, endpoint, send=fail_once) == (1, 0)
    assert alerts.notify_pending(seeded, endpoint, send=fail_once) == (0, 0)
    assert delivered[0] == delivered[1]
    assert delivered[0]["order_id"] == order.id
    assert delivered[0]["expected_minor"] == 4500
    assert delivered[0]["actual_minor"] == 45
    assert seeded.execute("SELECT notified_at FROM purchase_alerts").fetchone()[0]
    assert seeded.execute("SELECT COUNT(*) FROM purchase_alerts").fetchone()[0] == 1


def test_alert_delivery_requires_https(seeded):
    with pytest.raises(ValueError):
        alerts.notify_pending(seeded, "http://alerts.example.test/eventhub", send=lambda *_: None)


def test_existing_alert_table_gains_notification_column(tmp_path):
    conn = sqlite3.connect(tmp_path / "legacy.db")
    conn.execute(
        "CREATE TABLE purchase_alerts (id INTEGER PRIMARY KEY, order_id INTEGER, "
        "occurred_at TEXT, expected_minor INTEGER, actual_minor INTEGER, "
        "currency TEXT, reason TEXT, acknowledged_at TEXT)"
    )
    conn.commit()
    conn.close()
    upgraded = database.connect(tmp_path / "legacy.db")
    database.init_db(upgraded)
    columns = {row["name"] for row in upgraded.execute("PRAGMA table_info(purchase_alerts)")}
    assert "notified_at" in columns
    upgraded.close()
