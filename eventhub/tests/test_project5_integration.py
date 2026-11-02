"""Call 5 integration and characterization tests against isolated databases."""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
import requests

from eventhub import database, identity, purchasing


def csrf(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "A CSRF token must appear in the rendered form"
    return match.group(1)


def logged_in_session(base, email):
    session = requests.Session()
    token = csrf(session.get(base + "/login", timeout=10).text)
    response = session.post(base + "/login", data={
        "csrf_token": token, "email": email, "password": "correct-horse-123"
    }, allow_redirects=False, timeout=10)
    assert response.status_code == 302
    return session, csrf(session.get(base + "/events", timeout=10).text)


def test_two_buyers_final_ticket_repeated(live_server, app):
    """ticket-purchasing-008/010/011/012/013; logging-and-auditing-001/003:
    true overlapping HTTP requests."""
    db = database.connect(app.config["DATABASE_PATH"])
    try:
        a = identity.register_user(db, "Buyer A", "a@example.com", "correct-horse-123")
        b = identity.register_user(db, "Buyer B", "b@example.com", "correct-horse-123")
        db.execute("UPDATE events SET capacity=1, tickets_available=1 WHERE id=1")
        sessions = [logged_in_session(live_server, user.email) for user in (a, b)]
        rounds = int(os.environ.get("EVENTHUB_CONCURRENCY_ROUNDS", "200"))
        assert 1 <= rounds <= 2000
        for round_no in range(rounds):
            db.execute("DELETE FROM audit_log")
            db.execute("DELETE FROM orders")
            db.execute("UPDATE events SET tickets_available=1 WHERE id=1")
            barrier = Barrier(2)

            def buy(pair):
                session, token = pair
                barrier.wait(timeout=10)
                return session.post(live_server + "/events/1/purchase", data={
                    "csrf_token": token, "quantity": "1", "currency": "USD"
                }, allow_redirects=False, timeout=15)

            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(buy, sessions))
            assert [r.status_code for r in responses] == [302, 302], round_no
            assert sum("/orders/" in r.headers["Location"] for r in responses) == 1, round_no
            assert db.execute("SELECT tickets_available FROM events WHERE id=1").fetchone()[0] == 0, round_no
            assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1, round_no
            outcomes = [r[0] for r in db.execute("SELECT outcome FROM audit_log ORDER BY id")]
            assert sorted(outcomes) == ["fail", "success"], (round_no, outcomes)
    finally:
        for session, _ in locals().get("sessions", []):
            session.close()
        db.close()


def test_home_currency_hash_and_email_eligibility(app):
    """user-accounts-and-authentication-006; currency-support-001/002;
    student-discount-001. Email edits are characterized."""
    db = database.connect(app.config["DATABASE_PATH"])
    try:
        user = identity.register_user(db, "Student", "STU@USF.EDU", "correct-horse-123", "JPY")
        stored = db.execute("SELECT email, home_currency, password_hash FROM users WHERE id=?", (user.id,)).fetchone()
        assert (stored["email"], stored["home_currency"]) == ("stu@usf.edu", "JPY")
        assert "correct-horse-123" not in stored["password_hash"]
        first = purchasing.purchase(db, user, 1, 1, "USD")
        assert first.discount_percent > 0
        db.execute("UPDATE users SET email='student@example.com' WHERE id=?", (user.id,))
        updated = identity.get_user(db, user.id)
        second = purchasing.purchase(db, updated, 1, 1, "USD")
        assert second.discount_percent == 0
    finally:
        db.close()


def test_duplicate_submission_current_behavior(app, web):
    """Characterization: no EARS ID defines idempotency of repeated Confirm actions."""
    response = web.post("/register", {"name": "Buyer", "email": "buyer@example.com",
                                      "password": "correct-horse-123"})
    assert response.status_code == 302
    payload = {"quantity": "1", "currency": "USD"}
    first = web.post("/events/1/purchase", payload)
    second = web.post("/events/1/purchase", payload)
    assert "/orders/" in first.headers["Location"]
    assert "/orders/" in second.headers["Location"]
    db = database.connect(app.config["DATABASE_PATH"])
    try:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2
        assert db.execute("SELECT tickets_available FROM events WHERE id=1").fetchone()[0] == 198
        assert db.execute("SELECT COUNT(*) FROM audit_log WHERE outcome='success'").fetchone()[0] == 2
    finally:
        db.close()


@pytest.mark.parametrize("payload,reason", [
    ({"quantity": "0", "currency": "USD"}, "INVALID_QUANTITY"),
    ({"quantity": "-1", "currency": "USD"}, "INVALID_QUANTITY"),
    ({"quantity": "11", "currency": "USD"}, "INVALID_QUANTITY"),
    ({"quantity": "2.5", "currency": "USD"}, "INVALID_QUANTITY"),
    ({"currency": "USD"}, "INVALID_QUANTITY"),
    ({"quantity": "1", "currency": "ZZZ"}, "UNSUPPORTED_CURRENCY"),
    ({"quantity": "1"}, "UNSUPPORTED_CURRENCY"),
])
def test_direct_invalid_purchase_preserves_state(app, web, payload, reason):
    """ticket-purchasing-008/010; currency-support-005/006;
    logging-and-auditing-001/003."""
    web.post("/register", {"name": "Buyer", "email": "buyer@example.com",
                           "password": "correct-horse-123"})
    result = web.post("/events/1/purchase", payload, follow_redirects=True)
    assert result.status_code == 200 and b"flash-error" in result.data
    db = database.connect(app.config["DATABASE_PATH"])
    try:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
        assert db.execute("SELECT tickets_available FROM events WHERE id=1").fetchone()[0] == 200
        assert db.execute("SELECT reason_code FROM audit_log").fetchone()[0] == reason
    finally:
        db.close()


def test_bounded_excessive_invalid_requests(app, web):
    """Characterization: rate policy unspecified; 200 local invalid requests create no orders."""
    web.post("/register", {"name": "Buyer", "email": "buyer@example.com",
                           "password": "correct-horse-123"})
    for _ in range(200):
        assert web.post("/events/1/purchase", {"quantity": "0", "currency": "USD"}).status_code == 302
    db = database.connect(app.config["DATABASE_PATH"])
    try:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
        assert db.execute("SELECT tickets_available FROM events WHERE id=1").fetchone()[0] == 200
        assert db.execute("SELECT COUNT(*) FROM audit_log WHERE reason_code='INVALID_QUANTITY'").fetchone()[0] == 200
    finally:
        db.close()
