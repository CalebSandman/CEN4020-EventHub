"""Regression tests for the issues found during manual testing (Issues.md)."""
import pytest

from conftest import make_event
from eventhub import audit, database, inventory, maintenance, purchasing
from test_app_routes import db, register_and_login


def last(app):
    c = db(app)
    try:
        return audit.query(c, limit=1)[0]
    finally:
        c.close()


def count(app):
    c = db(app)
    try:
        return len(audit.query(c, limit=500))
    finally:
        c.close()


# Issue 1: audit log shows event number instead of name
def test_audit_records_event_name(seeded, buyer):
    purchasing.purchase(seeded, buyer, 1, 1, "USD")
    rec = audit.query(seeded)[0]
    assert rec.event_name == "Neon Harbor Tour" and rec.event_ref == "1"


def test_audit_event_name_is_none_for_nonexistent_event(seeded, buyer):
    with pytest.raises(purchasing.PurchaseError):
        purchasing.purchase(seeded, buyer, 9999, 1, "USD")
    rec = audit.query(seeded)[0]
    assert rec.event_name is None and rec.event_ref == "9999"


def test_admin_audit_page_shows_event_name(app, web):
    from test_app_routes import make_admin
    make_admin(app)
    web.login("ada@example.com", "admin-password-1")
    web.post("/events/1/quick-buy")
    assert b"Neon Harbor Tour" in web.get("/admin/audit").data


def test_old_databases_are_migrated_and_backfilled(tmp_path):
    path = tmp_path / "old.db"
    c = database.connect(path)
    database.init_db(c)
    c.execute("ALTER TABLE audit_log DROP COLUMN event_name")   # simulate the previous schema
    c.execute("INSERT INTO events (name,artist,venue,city,starts_at,base_price_cents,capacity,tickets_available)"
              " VALUES ('Old Show','a','v','c','2030-01-01',100,5,5)")
    c.execute("INSERT INTO audit_log (occurred_at,event_ref,outcome) VALUES ('t','1','fail')")
    database.init_db(c)                                         # app start-up
    assert audit.query(c)[0].event_name == "Old Show"
    database.init_db(c)                                         # idempotent
    c.close()


# Issue 2: failed purchases for invalid amounts must be logged
def test_checkout_with_more_than_max_tickets_is_audited(app, web):
    register_and_login(web)
    web.get(f"/events/1/checkout?quantity={purchasing.MAX_TICKETS_PER_ORDER + 1}&currency=USD")
    rec = last(app)
    assert (rec.outcome, rec.reason_code, rec.event_name) == ("fail", "INVALID_QUANTITY", "Neon Harbor Tour")
    assert rec.quantity == str(purchasing.MAX_TICKETS_PER_ORDER + 1) and rec.user_email == "bea@example.com"


def test_checkout_with_more_than_available_is_audited(app, web):
    register_and_login(web)
    c = db(app)
    eid = make_event(c, capacity=3)
    c.close()
    web.get(f"/events/{eid}/checkout?quantity=5&currency=USD")
    assert last(app).reason_code == "INSUFFICIENT_AVAILABILITY"


@pytest.mark.parametrize("qty", ["0", "-1", "abc"])
def test_checkout_with_other_invalid_quantities_is_audited(app, web, qty):
    register_and_login(web)
    web.get(f"/events/1/checkout?quantity={qty}&currency=USD")
    assert last(app).reason_code == "INVALID_QUANTITY"


def test_checkout_with_unsupported_currency_is_audited(app, web):
    register_and_login(web)
    web.get("/events/1/checkout?quantity=1&currency=XXX")
    assert last(app).reason_code == "UNSUPPORTED_CURRENCY"


# Issue 3: failed purchases on sold-out events must be logged
def test_sold_out_cards_still_have_a_double_click_target(app, web):
    c = db(app)
    eid = make_event(c, capacity=1, name="Tiny Gig")
    c.execute("UPDATE events SET tickets_available = 0 WHERE id = ?", (eid,))
    c.close()
    assert f'action="/events/{eid}/quick-buy"'.encode() in web.get("/events").data


def test_double_click_on_sold_out_event_is_audited(app, web):
    register_and_login(web)
    c = db(app)
    eid = make_event(c, capacity=1, name="Tiny Gig")
    c.execute("UPDATE events SET tickets_available = 0 WHERE id = ?", (eid,))
    c.close()
    r = web.post(f"/events/{eid}/quick-buy", follow_redirects=True)
    assert b"sold out" in r.data.lower()
    rec = last(app)
    assert (rec.outcome, rec.reason_code, rec.event_name) == ("fail", "SOLD_OUT", "Tiny Gig")


def test_checkout_click_after_last_ticket_taken_is_audited(app, web):
    """Buyer is on the event page; someone else buys the last ticket; buyer clicks Checkout."""
    register_and_login(web)
    c = db(app)
    eid = make_event(c, capacity=1)
    inventory.reserve(c, eid, 1)                      # the other buyer
    c.close()
    r = web.get(f"/events/{eid}/checkout?quantity=1&currency=USD", follow_redirects=True)
    assert b"sold out" in r.data.lower()
    assert last(app).reason_code == "SOLD_OUT"


def test_confirm_click_after_last_ticket_taken_is_audited(app, web):
    """Buyer reaches the checkout summary; someone else buys the last ticket; buyer confirms."""
    register_and_login(web)
    c = db(app)
    eid = make_event(c, capacity=1)
    c.close()
    assert web.get(f"/events/{eid}/checkout?quantity=1&currency=USD").status_code == 200
    before = count(app)
    c = db(app)
    inventory.reserve(c, eid, 1)                      # the other buyer
    c.close()
    r = web.post(f"/events/{eid}/purchase", {"quantity": "1", "currency": "USD"}, follow_redirects=True)
    assert b"sold out" in r.data.lower()
    assert count(app) == before + 1 and last(app).reason_code == "SOLD_OUT"


def test_successful_checkout_preview_is_not_logged_as_an_attempt(app, web):
    register_and_login(web)
    web.get("/events/1/checkout?quantity=1&currency=USD")
    assert count(app) == 0                            # only the confirmed purchase counts


def test_each_failure_is_logged_exactly_once(app, web):
    register_and_login(web)
    web.get("/events/1/checkout?quantity=99&currency=USD")
    assert count(app) == 1
    web.post("/events/1/purchase", {"quantity": "99", "currency": "USD"})
    assert count(app) == 2


def test_checkout_for_unknown_event_is_404_and_audited(app, web):
    register_and_login(web)
    assert web.get("/events/99999/checkout?quantity=1&currency=USD").status_code == 404
    assert last(app).reason_code == "EVENT_NOT_FOUND"


# Maintenance tools
def test_set_tickets(seeded):
    maintenance.set_tickets(seeded, 1, 7)
    assert inventory.available(seeded, 1) == 7
    maintenance.set_tickets(seeded, 1, 50, capacity=60)
    row = maintenance.list_events(seeded)[0]
    assert (row["tickets_available"], row["capacity"]) == (50, 60)


@pytest.mark.parametrize("args", [(999, 1), (1, -1), (1, 201), (1, 5, 0), (1, 11, 10)])
def test_set_tickets_rejects_bad_values(seeded, args):
    with pytest.raises(maintenance.MaintenanceError):
        maintenance.set_tickets(seeded, *args)


def test_reset_sales_restores_everything_but_users_and_rates(seeded, buyer):
    purchasing.purchase(seeded, buyer, 1, 3, "USD")
    with pytest.raises(purchasing.PurchaseError):
        purchasing.purchase(seeded, buyer, 1, 0, "USD")
    result = maintenance.reset_sales(seeded)
    assert result == {"orders_deleted": 1, "audit_records_deleted": 2}
    assert inventory.available(seeded, 1) == 200
    assert seeded.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    assert seeded.execute("SELECT COUNT(*) FROM exchange_rates").fetchone()[0] == 7
