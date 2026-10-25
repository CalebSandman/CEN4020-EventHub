import pytest

from eventhub import audit


def rec(conn, **kw):
    base = dict(user_id=1, user_email="a@b.co", event_ref=3, quantity=2, currency="USD", outcome="success")
    base.update(kw)
    return audit.record(conn, **base)


def test_record_has_all_required_fields(conn):
    rec(conn)
    r = audit.query(conn)[0]
    assert r.occurred_at and r.user_email == "a@b.co" and r.event_ref == "3"
    assert (r.quantity, r.currency, r.outcome) == ("2", "USD", "success")


def test_failure_with_reason_and_garbage_input_is_stored_safely(conn):
    rec(conn, outcome="fail", reason_code="INVALID_QUANTITY", quantity="-5\n<b>" + "x" * 500)
    r = audit.query(conn)[0]
    assert r.outcome == "fail" and r.reason_code == "INVALID_QUANTITY"
    assert len(r.quantity) <= 64 and "\n" not in r.quantity


def test_anonymous_attempt_can_be_recorded(conn):
    rec(conn, user_id=None, user_email=None, outcome="fail", reason_code="NOT_AUTHENTICATED")
    assert audit.query(conn)[0].user_email is None


def test_invalid_outcome_rejected(conn):
    with pytest.raises(ValueError):
        rec(conn, outcome="maybe")


def test_query_filters_and_order(conn):
    rec(conn, user_email="one@x.io")
    rec(conn, user_email="two@x.io", outcome="fail", reason_code="SOLD_OUT")
    rec(conn, user_email="two@x.io", outcome="fail", reason_code="UNSUPPORTED_CURRENCY")
    assert [r.user_email for r in audit.query(conn)][0] == "two@x.io"       # newest first
    assert len(audit.query(conn, outcome="fail")) == 2
    assert len(audit.query(conn, user_email="ONE")) == 1
    assert len(audit.query(conn, reason_code="sold_out")) == 1
    assert len(audit.query(conn, user_email="%")) == 0                       # wildcard is literal
    with pytest.raises(ValueError):
        audit.query(conn, outcome="bogus")


def test_limit_is_bounded(conn):
    for _ in range(3):
        rec(conn)
    assert len(audit.query(conn, limit=2)) == 2
    assert len(audit.query(conn, limit=-5)) == 1
