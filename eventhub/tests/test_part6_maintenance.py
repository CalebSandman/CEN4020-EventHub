"""Call 6 regression coverage through pricing, purchases and HTTP routes."""
from decimal import Decimal

import pytest

from conftest import make_event
from eventhub import administration, alerts, audit, database, identity, localization, pricing, purchasing


EXPECTED = {
    "USD": (3000, 2, "$30.00 USD"),
    "EUR": (2760, 2, "€27.60 EUR"),
    "GBP": (2370, 2, "£23.70 GBP"),
    "CAD": (4080, 2, "CA$40.80 CAD"),
    "MXN": (51600, 2, "MX$516.00 MXN"),
    "JPY": (4500, 0, "¥4,500 JPY"),
    "KWD": (9210, 3, "KD9.210 KWD"),
}


@pytest.mark.parametrize("code", EXPECTED)
def test_every_currency_purchase_matches_quote_audit_and_display(seeded, buyer, code):
    event_id = make_event(seeded, name=f"Show {code}", price_cents=3000)
    expected, decimals, display = EXPECTED[code]
    quote = purchasing.preview_checkout(seeded, buyer, event_id, 1, code).quote
    charged = []
    order = purchasing.purchase(seeded, buyer, event_id, 1, code,
                                payment=lambda user, minor, currency: charged.append((minor, currency)) or True)
    assert quote.total_minor == order.total_minor == expected
    assert (order.currency_decimals, charged) == (decimals, [(expected, code)])
    assert localization.format_money(order.total_minor, code, decimals) == display
    record = audit.query(seeded)[0]
    assert (record.order_id, record.outcome, record.currency) == (order.id, "success", code)


@pytest.mark.parametrize("code", EXPECTED)
def test_every_currency_student_discount_is_applied_before_rounding(seeded, student, code):
    event_id = make_event(seeded, name=f"Student {code}", price_cents=3000)
    order = purchasing.purchase(seeded, student, event_id, 1, code)
    assert order.discount_percent == Decimal("10")
    assert order.total_minor == pricing.calculate_price(seeded, 3000, 1, True, code).total_minor
    assert alerts.scan_orders(seeded) == 0


def test_yen_4500_incident_never_becomes_45(seeded, buyer):
    event_id = make_event(seeded, name="Yen incident", price_cents=3000)
    order = purchasing.purchase(seeded, buyer, event_id, 1, "JPY")
    assert order.total_minor == 4500
    assert localization.format_money(order.total_minor, "JPY", 0) == "¥4,500 JPY"
    assert seeded.execute("SELECT total_minor FROM orders WHERE id=?", (order.id,)).fetchone()[0] == 4500


def test_alert_scan_detects_one_percent_total_without_discount_false_positive(seeded, buyer, student):
    event_id = make_event(seeded, name="Alert show", price_cents=3000)
    bad = purchasing.purchase(seeded, buyer, event_id, 1, "JPY")
    good = purchasing.purchase(seeded, student, event_id, 1, "JPY")
    seeded.execute("UPDATE orders SET total_minor=45 WHERE id=?", (bad.id,))
    assert alerts.scan_orders(seeded) == 1
    assert alerts.scan_orders(seeded) == 0
    row = seeded.execute("SELECT * FROM purchase_alerts").fetchone()
    assert (row["order_id"], row["expected_minor"], row["actual_minor"]) == (bad.id, 4500, 45)
    assert row["order_id"] != good.id


def test_admin_rate_workflow_and_historical_order(app, web):
    conn = database.connect(app.config["DATABASE_PATH"])
    identity.create_admin_user(conn, "Admin", "admin@example.com", "admin-pass-123")
    identity.register_user(conn, "Buyer", "buyer@example.com", "buyer-pass-123")
    conn.close()


    web.login("buyer@example.com", "buyer-pass-123")
    first = web.post("/events/1/purchase", {"quantity": "1", "currency": "EUR"})
    assert first.status_code == 302
    assert web.post("/admin/rates", {"currency": "EUR", "rate": "0.5"}).status_code == 403
    web.post("/logout")
    web.login("admin@example.com", "admin-pass-123")
    assert web.post("/admin/rates", {"currency": "EUR", "rate": "0.5"}).status_code == 302
    assert web.post("/admin/rates", {"currency": "EUR", "rate": "NaN"}).status_code == 302
    conn = database.connect(app.config["DATABASE_PATH"])
    assert pricing.load_currencies(conn)["EUR"].rate == Decimal("0.5")
    row = conn.execute("SELECT old_rate,new_rate FROM rate_audit").fetchone()
    assert tuple(row) == ("0.92", "0.5")
    conn.close()
    web.post("/logout")
    web.login("buyer@example.com", "buyer-pass-123")
    second = web.post("/events/1/purchase", {"quantity": "1", "currency": "EUR"})
    assert second.status_code == 302
    conn = database.connect(app.config["DATABASE_PATH"])
    orders = conn.execute("SELECT total_minor,exchange_rate FROM orders ORDER BY id").fetchall()
    assert [tuple(r) for r in orders] == [(8188, "0.92"), (4450, "0.5")]
    conn.close()


def test_rate_change_after_checkout_requires_new_confirmation(app, web):
    web.post("/register", {"name": "Buyer", "email": "preview@example.com",
                           "password": "buyer-pass-123"})
    original = web.get("/events/1/checkout?quantity=1&currency=EUR")
    assert "€81.88 EUR" in original.data.decode()
    conn = database.connect(app.config["DATABASE_PATH"])
    admin = identity.create_admin_user(conn, "Admin", "preview-admin@example.com", "admin-pass-123")
    administration.update_rate(conn, admin, "EUR", "0.5")
    conn.close()
    changed = web.post("/events/1/purchase", {"quantity": "1", "currency": "EUR"})
    assert changed.status_code == 302 and "/checkout" in changed.headers["Location"]
    new_quote = web.get(changed.headers["Location"])
    assert "€44.50 EUR" in new_quote.data.decode()
    conn = database.connect(app.config["DATABASE_PATH"])
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert audit.query(conn)[0].reason_code == purchasing.PRICE_CHANGED
    conn.close()


def test_admin_alert_page_surfaces_bad_historical_total(app, web):
    conn = database.connect(app.config["DATABASE_PATH"])
    identity.create_admin_user(conn, "Admin", "alert-admin@example.com", "admin-pass-123")
    conn.close()
    web.post("/register", {"name": "Buyer", "email": "alert-buyer@example.com",
                           "password": "buyer-pass-123"})
    purchase = web.post("/events/1/purchase", {"quantity": "1", "currency": "JPY"})
    assert purchase.status_code == 302
    conn = database.connect(app.config["DATABASE_PATH"])
    conn.execute("UPDATE orders SET total_minor=133 WHERE currency='JPY'")
    conn.close()
    assert web.get("/admin/alerts").status_code == 403
    web.post("/logout")
    web.login("alert-admin@example.com", "admin-pass-123")
    page = web.get("/admin/alerts").data.decode()
    assert "Purchase alerts" in page and "¥13,350 JPY" in page and "¥133 JPY" in page


def test_locale_selection_rendering_fallback_and_value_preservation(app, web):
    assert b"Upcoming events" in web.get("/events").data
    assert web.post("/locale", {"locale": "es_ES", "next": "/events"}).status_code == 302
    page = web.get("/events").data.decode()
    assert "Próximos eventos" in page and '<html lang="es">' in page
    assert localization.translate("missing key", "es_ES") == "missing key"
    assert localization.format_date("2026-11-08T20:00", "en_US").startswith("11/08/2026")
    assert localization.format_date("2026-11-08T20:00", "es_ES").startswith("08/11/2026")
    assert localization.format_money(4500, "JPY", 0, "es_ES") == "4.500 ¥ JPY"
    assert localization.format_money(4500, "JPY", 0, "en_US") == "¥4,500 JPY"
    web.post("/register", {"name": "Buyer", "email": "buyer@example.com", "password": "buyer-pass-123"})
    checkout = web.get("/events/1/checkout?quantity=1&currency=JPY").data.decode()
    assert "¥ JPY" in checkout and "Pagar" in checkout
    response = web.post("/events/1/purchase", {"quantity": "1", "currency": "JPY"})
    assert response.status_code == 302
    confirmation = web.get(response.headers["Location"]).data.decode()
    assert "13.350 ¥ JPY" in confirmation
    conn = database.connect(app.config["DATABASE_PATH"])
    assert conn.execute("SELECT total_minor FROM orders").fetchone()[0] == 13350
    conn.close()
