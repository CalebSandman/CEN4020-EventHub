"""End-to-end tests through Flask: guards, CSRF, rendering, purchase flow."""
import re

from conftest import make_event
from eventhub import database, identity, inventory, purchasing


def db(app):
    return database.connect(app.config["DATABASE_PATH"])


def register_and_login(web, email="bea@example.com", name="Bea"):
    r = web.post("/register", {"name": name, "email": email, "password": "correct-horse-1"})
    assert r.status_code == 302
    return r


def make_admin(app, email="ada@example.com", pw="admin-password-1"):
    c = db(app)
    identity.create_admin_user(c, "Ada", email, pw)
    c.close()


# ---- pages / browsing ------------------------------------------------------ #
def test_event_list_and_detail(web):
    r = web.get("/events")
    assert r.status_code == 200 and b"Neon Harbor Tour" in r.data
    d = web.get("/events/1")
    assert d.status_code == 200 and b"tickets available" in d.data       # availability shown
    assert web.get("/events/99999").status_code == 404


def test_responsive_markup(web):
    assert b'name="viewport"' in web.get("/events").data


def test_search_by_artist_and_venue(web):
    assert b"Acoustic Evenings" in web.get("/events?field=artist&q=luna").data
    page = web.get("/events?field=venue&q=orpheum").data
    assert b"Last Call Comedy Night" in page and b"Neon Harbor" not in page


def test_no_match_message_then_full_list(web):
    page = web.get("/events?field=artist&q=nobody-here").data
    assert b"No matching events were found" in page and b"Neon Harbor Tour" in page


def test_search_text_is_escaped(web):
    page = web.get('/events?q=<script>alert(1)</script>').data
    assert b"<script>alert(1)</script>" not in page
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_event_cards_support_click_and_double_click_hooks(web):
    page = web.get("/events").data.decode()
    assert 'data-detail-url="/events/1"' in page and 'action="/events/1/quick-buy"' in page
    assert "<script>" not in page.replace('<script src', '')            # no inline scripts


# ---- auth ------------------------------------------------------------------ #
def test_protected_pages_redirect_to_login_with_return_url(web):
    r = web.get("/orders")
    assert r.status_code == 302 and "/login?next=/orders" in r.headers["Location"]
    r = web.get("/events/1/checkout?quantity=2&currency=EUR")
    assert r.status_code == 302 and r.headers["Location"].startswith("/login?next=")


def test_login_returns_to_requested_page(web):
    register_and_login(web)
    web.post("/logout")
    r = web.get("/orders")
    nxt = r.headers["Location"].split("next=")[1]
    r = web.post("/login", {"email": "bea@example.com", "password": "correct-horse-1", "next": nxt})
    assert r.status_code == 302 and r.headers["Location"] == "/orders"


def test_login_rejects_open_redirect(web):
    register_and_login(web)
    web.post("/logout")
    r = web.post("/login", {"email": "bea@example.com", "password": "correct-horse-1", "next": "https://evil.example"})
    assert r.headers["Location"] == "/"


def test_bad_login_and_registration_errors(web):
    assert web.post("/login", {"email": "x@y.zz", "password": "nope-nope-1"}).status_code == 401
    r = web.post("/register", {"name": "", "email": "a@b.co", "password": "longenough1"})
    assert r.status_code == 400


def test_unauthenticated_sees_no_protected_data_and_no_records_created(app, web):
    web.get("/orders"); web.get("/events/1/checkout?quantity=1&currency=USD")
    r = web.post("/events/1/purchase", {"quantity": "1", "currency": "USD"})
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    c = db(app)
    assert c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert inventory.available(c, 1) == 200


def test_session_expires(app, web):
    register_and_login(web)
    assert web.get("/orders").status_code == 200
    with web.client.session_transaction() as s:
        s["last_seen"] = s["last_seen"] - 31 * 60
    assert web.get("/orders").status_code == 302


# ---- CSRF ------------------------------------------------------------------ #
def test_post_without_csrf_token_is_rejected(client):
    assert client.post("/login", data={"email": "a@b.co", "password": "x"}).status_code == 400
    assert client.post("/currency", data={"currency": "EUR"}).status_code == 400


# ---- currency -------------------------------------------------------------- #
def test_currency_selection_changes_displayed_prices(web):
    assert b"89.00 USD" in web.get("/events").data
    web.post("/currency", {"currency": "JPY", "next": "/events"})
    assert b"13,350 JPY" in web.get("/events").data      # 89 * 150


def test_unsupported_currency_selection_rejected(web):
    web.post("/currency", {"currency": "XXX"})
    assert b"89.00 USD" in web.get("/events").data


# ---- purchase flow ---------------------------------------------------------- #
def test_full_purchase_flow(app, web):
    register_and_login(web)
    co = web.get("/events/1/checkout?quantity=2&currency=EUR")
    assert co.status_code == 200
    page = co.data.decode()
    assert "Quantity" in page and "EUR" in page and "163.76 EUR" in page      # 2 * 89 * 0.92
    assert co.headers["Cache-Control"] == "no-store"
    r = web.post("/events/1/purchase", {"quantity": "2", "currency": "EUR"})
    assert r.status_code == 302
    conf = web.get(r.headers["Location"])
    text = conf.data.decode()
    for needle in ("Neon Harbor Tour", "Quantity purchased", "EUR", "1 USD = 0.92 EUR", "163.76 EUR"):
        assert needle in text
    assert conf.headers["Cache-Control"] == "no-store"
    assert "confirmation email" not in text.lower() or "no email" in text.lower()
    hist = web.get("/orders").data
    assert b"Neon Harbor Tour" in hist
    c = db(app)
    assert inventory.available(c, 1) == 198
    assert c.execute("SELECT outcome FROM audit_log").fetchone()[0] == "success"


def test_client_supplied_total_is_ignored(app, web):
    register_and_login(web)
    r = web.post("/events/1/purchase", {"quantity": "1", "currency": "USD", "total": "0.01", "price": "0"})
    text = web.get(r.headers["Location"]).data.decode()
    assert "89.00 USD" in text


def test_server_rejects_bad_inputs_with_distinct_messages(app, web):
    register_and_login(web)
    cases = [("0", "USD", "cannot be zero"), ("-2", "USD", "cannot be negative"),
             ("9999", "USD", "at most"), ("2", "XXX", "not supported"), ("x", "USD", "whole number")]
    for qty, cur, msg in cases:
        r = web.post("/events/1/purchase", {"quantity": qty, "currency": cur}, follow_redirects=True)
        assert msg.encode() in r.data, (qty, cur)
    c = db(app)
    assert inventory.available(c, 1) == 200
    assert c.execute("SELECT COUNT(*) FROM audit_log WHERE outcome='fail'").fetchone()[0] == len(cases)


def test_sold_out_event_error(app, web):
    register_and_login(web)
    c = db(app)
    eid = make_event(c, capacity=1)
    c.close()
    web.post(f"/events/{eid}/purchase", {"quantity": "1", "currency": "USD"})
    r = web.post(f"/events/{eid}/purchase", {"quantity": "1", "currency": "USD"}, follow_redirects=True)
    assert b"sold out" in r.data.lower()


def test_abandoned_checkout_changes_nothing(app, web):
    register_and_login(web)
    web.get("/events/1/checkout?quantity=3&currency=USD")       # then walks away
    c = db(app)
    assert inventory.available(c, 1) == 200
    assert c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_student_discount_end_to_end(web):
    register_and_login(web, email="Stu@USF.EDU", name="Stu")
    page = web.get("/events/1/checkout?quantity=1&currency=USD").data.decode()
    assert "Student discount" in page and "80.10 USD" in page      # 89 - 10% (placeholder %)


def test_double_click_buys_one_ticket(app, web):
    register_and_login(web)
    r = web.post("/events/2/quick-buy")
    assert r.status_code == 302 and "/orders/" in r.headers["Location"]
    c = db(app)
    assert inventory.available(c, 2) == 119
    assert c.execute("SELECT quantity FROM orders").fetchone()[0] == 1


def test_double_click_requires_login_and_creates_nothing(app, web):
    r = web.post("/events/2/quick-buy")
    assert r.status_code == 302 and "/login?next=/events/2" in r.headers["Location"]
    c = db(app)
    assert c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert inventory.available(c, 2) == 120


def test_quick_buy_sold_out_shows_error(app, web):
    register_and_login(web)
    c = db(app)
    eid = make_event(c, capacity=1)
    c.close()
    web.post(f"/events/{eid}/quick-buy")
    r = web.post(f"/events/{eid}/quick-buy", follow_redirects=True)
    assert b"sold out" in r.data.lower()


def test_cannot_open_another_users_order(app, web):
    register_and_login(web)
    r = web.post("/events/1/purchase", {"quantity": "1", "currency": "USD"})
    order_url = r.headers["Location"]
    web.post("/logout")
    register_and_login(web, email="other@example.com", name="Other")
    assert web.get(order_url).status_code == 404


# ---- admin / RBAC ----------------------------------------------------------- #
def test_buyer_denied_admin_pages(web):
    register_and_login(web)
    for url in ("/admin/", "/admin/rates", "/admin/audit"):
        assert web.get(url).status_code == 403
    assert web.post("/admin/rates", {"currency": "EUR", "rate": "0.1"}).status_code == 403


def test_anonymous_redirected_from_admin(web):
    assert web.get("/admin/rates").status_code == 302
    assert web.get("/admin/audit").status_code == 302


def test_buyer_cannot_become_admin_by_registering_with_role_field(app, web):
    web.post("/register", {"name": "Eve", "email": "eve@example.com", "password": "longenough1", "role": "admin"})
    c = db(app)
    assert c.execute("SELECT role FROM users WHERE email='eve@example.com'").fetchone()[0] == "buyer"


def test_admin_updates_rate_and_reviews_audit(app, web):
    make_admin(app)
    register_and_login(web, email="bea@example.com")
    web.post("/events/1/purchase", {"quantity": "0", "currency": "USD"})        # a failed attempt
    web.post("/logout")
    web.login("ada@example.com", "admin-password-1")
    assert web.get("/admin/rates").status_code == 200
    r = web.post("/admin/rates", {"currency": "EUR", "rate": "0.5"}, follow_redirects=True)
    assert b"Exchange rate updated" in r.data
    web.post("/currency", {"currency": "EUR"})
    assert b"44.50 EUR" in web.get("/events").data
    r = web.post("/admin/rates", {"currency": "EUR", "rate": "-1"}, follow_redirects=True)
    assert b"greater than zero" in r.data
    audit_page = web.get("/admin/audit?outcome=fail&email=bea").data
    assert b"INVALID_QUANTITY" in audit_page and b"bea@example.com" in audit_page


# ---- headers / errors ------------------------------------------------------- #
def test_security_headers_and_error_pages(web):
    r = web.get("/events")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in r.headers["Content-Security-Policy"]
    assert web.get("/nope").status_code == 404
    assert web.get("/orders/abc").status_code in (302, 404)
