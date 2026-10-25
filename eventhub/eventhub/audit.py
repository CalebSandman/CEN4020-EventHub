"""Audit Trail component.

The single place purchase attempts are recorded (routes never write audit rows
themselves). ``record`` does not commit: on success the purchase path calls it
inside the order transaction so the audit row and the order are atomic; on
failure it is called after rollback, where autocommit persists it.

Open question (docs/open-questions.md Q3): retention period is undefined, so
nothing is purged automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from . import database

OUTCOME_SUCCESS = "success"
OUTCOME_FAIL = "fail"
OUTCOMES = (OUTCOME_SUCCESS, OUTCOME_FAIL)
_MAX_FIELD = 64
MAX_QUERY_LIMIT = 500


@dataclass(frozen=True)
class AuditRecord:
    id: int
    occurred_at: str
    user_id: int | None
    user_email: str | None
    event_ref: str | None
    event_name: str | None
    quantity: str | None
    currency: str | None
    outcome: str
    reason_code: str | None
    order_id: int | None


def _clip(value) -> str | None:
    """Store what the client sent (even if invalid) but bound its size."""
    if value is None:
        return None
    text = "".join(ch if ch.isprintable() else "?" for ch in str(value))
    return text[:_MAX_FIELD]


def _event_name(conn, ref) -> str | None:
    """Name of the event at the time of the attempt (None if the ref is not a real event)."""
    try:
        event_id = int(str(ref).strip())
    except (TypeError, ValueError):
        return None
    row = conn.execute("SELECT name FROM events WHERE id = ?", (event_id,)).fetchone()
    return row["name"] if row else None


def record(conn, *, user_id, user_email, event_ref, quantity, currency, outcome,
           reason_code: str | None = None, order_id: int | None = None,
           now: datetime | None = None) -> int:
    """Write one purchase-attempt row: time, user, event, quantity, currency, outcome."""
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}")
    stamp = database.to_iso(now or database.utcnow())
    cur = conn.execute(
        "INSERT INTO audit_log (occurred_at, user_id, user_email, event_ref, event_name, quantity, "
        "currency, outcome, reason_code, order_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (stamp, user_id, _clip(user_email), _clip(event_ref), _clip(_event_name(conn, event_ref)),
         _clip(quantity), _clip(currency),
         outcome, _clip(reason_code), order_id),
    )
    return cur.lastrowid


def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def query(conn, *, outcome: str | None = None, user_email: str | None = None,
          reason_code: str | None = None, limit: int = 100) -> list[AuditRecord]:
    """Newest-first records with optional filters (used by Administration only)."""
    clauses, params = [], []
    if outcome:
        if outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {OUTCOMES}")
        clauses.append("outcome = ?")
        params.append(outcome)
    if user_email:
        clauses.append("user_email LIKE ? ESCAPE '\\'")
        params.append(_like(user_email.strip().lower()))
    if reason_code:
        clauses.append("reason_code = ?")
        params.append(reason_code.strip().upper())
    limit = max(1, min(int(limit), MAX_QUERY_LIMIT))
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM audit_log {where} ORDER BY id DESC LIMIT ?", (*params, limit)
    ).fetchall()
    return [AuditRecord(**{k: r[k] for k in r.keys()}) for r in rows]
