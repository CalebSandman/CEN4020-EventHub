"""Non-destructive SQLite backup and verification for operations drills."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

REQUIRED_TABLES = ("users", "events", "exchange_rates", "orders", "audit_log", "purchase_alerts")


def _open_readonly(path):
    uri = "file:" + quote(path.as_posix(), safe="/:") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=10)


def verify_backup(path):
    """Read a backup without modifying it and return its key row counts."""
    target = Path(path).resolve()
    if not target.is_file():
        raise ValueError(f"Backup does not exist: {target}")
    with closing(_open_readonly(target)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Backup failed SQLite integrity_check")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = set(REQUIRED_TABLES) - tables
        if missing:
            raise ValueError(f"Backup is missing EventHub tables: {sorted(missing)}")
        return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in REQUIRED_TABLES}


def backup_database(source, destination):
    """Create a new online backup and verify it; never overwrite a prior copy."""
    src = Path(source).resolve()
    dest = Path(destination).resolve()
    if not src.is_file():
        raise ValueError(f"Source database does not exist: {src}")
    if src == dest:
        raise ValueError("Backup destination must differ from source")
    if not dest.parent.is_dir():
        raise ValueError(f"Backup destination directory does not exist: {dest.parent}")
    with dest.open("xb"):
        pass
    try:
        with closing(_open_readonly(src)) as source_conn, closing(sqlite3.connect(dest)) as dest_conn:
            source_conn.backup(dest_conn)
        return verify_backup(dest)
    except BaseException:
        dest.unlink()
        raise
