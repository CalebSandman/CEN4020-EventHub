"""Browser system tests: real HTTP, rendered UI, and persistent state."""
from uuid import uuid4

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from eventhub import database


def wait(browser, locator):
    return WebDriverWait(browser, 10).until(EC.visibility_of_element_located(locator))


def register(browser, base, currency="USD", email=None):
    email = email or f"buyer-{uuid4().hex}@example.com"
    browser.get(base + "/register")
    wait(browser, (By.ID, "name")).send_keys("Browser Buyer")
    browser.find_element(By.ID, "email").send_keys(email)
    browser.find_element(By.ID, "password").send_keys("correct-horse-123")
    Select(browser.find_element(By.ID, "home_currency")).select_by_value(currency)
    browser.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    wait(browser, (By.LINK_TEXT, "My orders"))
    return email


def test_complete_purchase_journey_and_persistence(browser, live_server, app):
    """user-accounts-and-authentication-001/003; event-browsing-and-searching-001/002/004/005;
    currency-support-001/003/010; ticket-purchasing-001/010;
    order-history-and-confirmations-001/002; logging-and-auditing-001.
    """
    email = register(browser, live_server, "GBP")
    browser.find_element(By.CSS_SELECTOR, "form[action='/logout'] button").click()
    wait(browser, (By.LINK_TEXT, "Log in")).click()
    wait(browser, (By.ID, "email")).send_keys(email)
    browser.find_element(By.ID, "password").send_keys("correct-horse-123")
    browser.find_element(By.XPATH, "//button[normalize-space()='Log in']").click()
    wait(browser, (By.LINK_TEXT, "My orders"))
    assert Select(browser.find_element(By.ID, "currency-select")).first_selected_option.text == "GBP"
    browser.find_element(By.ID, "q").send_keys("Neon")
    search_form = browser.find_element(By.CSS_SELECTOR, "form.search")
    search_form.find_element(By.TAG_NAME, "button").click()
    WebDriverWait(browser, 10).until(EC.staleness_of(search_form))
    wait(browser, (By.LINK_TEXT, "Neon Harbor Tour")).click()
    wait(browser, (By.ID, "quantity"))
    assert "tickets available" in browser.find_element(By.TAG_NAME, "body").text
    Select(browser.find_element(By.ID, "cur")).select_by_value("EUR")
    browser.find_element(By.ID, "quantity").clear()
    browser.find_element(By.ID, "quantity").send_keys("2")
    browser.find_element(By.XPATH, "//button[normalize-space()='Checkout']").click()
    wait(browser, (By.XPATH, "//h1[normalize-space()='Checkout']"))
    assert "Selected payment currency\nEUR" in browser.find_element(By.TAG_NAME, "body").text
    assert "Original ticket price (USD)\n89.00 USD" in browser.find_element(By.TAG_NAME, "body").text
    assert "163.76 EUR" in browser.find_element(By.TAG_NAME, "body").text
    browser.find_element(By.XPATH, "//button[contains(., 'Confirm purchase')]").click()
    wait(browser, (By.XPATH, "//h1[normalize-space()='Order confirmation']"))
    assert "Final total (mock charge)\n163.76 EUR" in browser.find_element(By.TAG_NAME, "body").text
    browser.find_element(By.PARTIAL_LINK_TEXT, "Order history").click()
    wait(browser, (By.XPATH, "//h1[normalize-space()='My orders']"))
    assert "Neon Harbor Tour" in browser.find_element(By.TAG_NAME, "body").text
    conn = database.connect(app.config["DATABASE_PATH"])
    try:
        order = conn.execute("SELECT o.*, u.email FROM orders o JOIN users u ON u.id=o.user_id").fetchone()
        assert (order["email"], order["quantity"], order["currency"], order["total_minor"]) == (email, 2, "EUR", 16376)
        assert conn.execute("SELECT tickets_available FROM events WHERE id=1").fetchone()[0] == 198
        assert conn.execute("SELECT outcome, order_id FROM audit_log").fetchone()["order_id"] == order["id"]
    finally:
        conn.close()


def test_browser_auth_search_and_access_control(browser, live_server, app):
    """user-accounts-and-authentication-005; event-browsing-and-searching-003/009/010;
    server-side-validation-and-security-007."""
    browser.get(live_server + "/orders")
    wait(browser, (By.XPATH, "//h1[normalize-space()='Log in']"))
    register(browser, live_server)
    browser.get(live_server + "/events?field=venue&q=Orpheum")
    assert "Last Call Comedy Night" in browser.find_element(By.TAG_NAME, "body").text
    browser.get(live_server + "/events?field=artist&q=no-such-artist-987")
    body = browser.find_element(By.TAG_NAME, "body").text
    assert "No matching events were found" in body and "Neon Harbor Tour" in body
    browser.get(live_server + "/admin/audit")
    assert "Access denied" in browser.find_element(By.TAG_NAME, "body").text


def test_browser_invalid_quantity_is_audited(browser, live_server, app):
    """server-side-validation-and-security-002; logging-and-auditing-001/003;
    regression for frontend bypass."""
    register(browser, live_server)
    browser.get(live_server + "/events/1")
    qty = wait(browser, (By.ID, "quantity"))
    qty.clear()
    qty.send_keys("0")
    browser.find_element(By.XPATH, "//button[normalize-space()='Checkout']").click()
    assert "cannot be zero" in wait(browser, (By.CSS_SELECTOR, "[role=alert]")).text
    conn = database.connect(app.config["DATABASE_PATH"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
        assert conn.execute("SELECT tickets_available FROM events WHERE id=1").fetchone()[0] == 200
        assert conn.execute("SELECT reason_code FROM audit_log").fetchone()[0] == "INVALID_QUANTITY"
    finally:
        conn.close()
