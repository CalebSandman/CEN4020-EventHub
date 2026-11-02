import threading

import pytest

from conftest import make_event
from eventhub import audit, catalog, database, identity, inventory, pricing, purchasing
from eventhub.purchasing import PurchaseError


def attempts(conn):
    return audit.query(conn, limit=500)


def fail_code(fn):
    with pytest.raises(PurchaseError) as err:
        fn()
    return err.value.code


# ---- happy path ----------------------------------------------------------- #
def test_successful_purchase(seeded, buyer):
    eid = make_event(seeded, capacity=5, price_cents=5550)
    order = purchasing.purchase(seeded, buyer, eid, "2", "eur")
    assert (order.quantity, order.currency, order.total_minor) == (2, "EUR", 10212)  # 111.00*0.92
    assert order.exchange_rate == pricing.load_currencies(seeded)["EUR"].rate
    assert inventory.available(seeded, eid) == 3
    log = attempts(seeded)
    assert len(log) == 1 and log[0].outcome == "success" and log[0].order_id == order.id


def test_student_gets_discount_and_order_records_it(seeded, student):
    eid = make_event(seeded, price_cents=10000)
    order = purchasing.purchase(seeded, student, eid, 1, "USD")
    assert order.total_minor == int(10000 * (100 - pricing.STUDENT_DISCOUNT_PERCENT) / 100)
    assert order.discount_percent == pricing.STUDENT_DISCOUNT_PERCENT


def test_buyer_gets_no_discount(seeded, buyer):
    eid = make_event(seeded, price_cents=10000)
    assert purchasing.purchase(seeded, buyer, eid, 1, "USD").total_minor == 10000


def test_order_keeps_rate_after_admin_changes_it(seeded, buyer):
    eid = make_event(seeded, price_cents=10000)
    order = purchasing.purchase(seeded, buyer, eid, 1, "EUR")
    seeded.execute("UPDATE exchange_rates SET rate='2' WHERE currency='EUR'")
    again = purchasing.get_order(seeded, buyer, order.id)
    assert again.total_minor == order.total_minor and again.exchange_rate == order.exchange_rate


# ---- validation & distinct errors ---------------------------------------- #
@pytest.mark.parametrize("qty,fragment", [
    (0, "zero"), ("0", "zero"), (-1, "negative"), ("-3", "negative"),
    (purchasing.MAX_TICKETS_PER_ORDER + 1, "at most"), (10**12, "at most"),
    ("abc", "whole number"), ("1.5", "whole number"), ("", "whole number"),
    (None, "whole number"), (True, "whole number"), ("1e3", "whole number"),
])
def test_invalid_quantities(seeded, buyer, qty, fragment):
    eid = make_event(seeded, capacity=50)
    with pytest.raises(PurchaseError) as err:
        purchasing.purchase(seeded, buyer, eid, qty, "USD")
    assert err.value.code == purchasing.INVALID_QUANTITY and fragment in err.value.message
    assert inventory.available(seeded, eid) == 50


def test_unsupported_currency(seeded, buyer):
    eid = make_event(seeded)
    assert fail_code(lambda: purchasing.purchase(seeded, buyer, eid, 1, "XXX")) == purchasing.UNSUPPORTED_CURRENCY
    assert fail_code(lambda: purchasing.purchase(seeded, buyer, eid, 1, None)) == purchasing.UNSUPPORTED_CURRENCY


def test_unknown_event(seeded, buyer):
    assert fail_code(lambda: purchasing.purchase(seeded, buyer, 99999, 1, "USD")) == purchasing.EVENT_NOT_FOUND
    assert fail_code(lambda: purchasing.purchase(seeded, buyer, "abc", 1, "USD")) == purchasing.EVENT_NOT_FOUND


def test_sold_out_vs_insufficient_are_distinct(seeded, buyer):
    eid = make_event(seeded, capacity=2)
    assert fail_code(lambda: purchasing.purchase(seeded, buyer, eid, 3, "USD")) == purchasing.INSUFFICIENT_AVAILABILITY
    purchasing.purchase(seeded, buyer, eid, 2, "USD")
    assert fail_code(lambda: purchasing.purchase(seeded, buyer, eid, 1, "USD")) == purchasing.SOLD_OUT


def test_cannot_exceed_availability(seeded, buyer):
    eid = make_event(seeded, capacity=3)
    purchasing.purchase(seeded, buyer, eid, 2, "USD")
    with pytest.raises(PurchaseError):
        purchasing.purchase(seeded, buyer, eid, 2, "USD")
    assert inventory.available(seeded, eid) == 1


def test_anonymous_purchase_rejected_and_creates_no_order(seeded):
    eid = make_event(seeded)
    assert fail_code(lambda: purchasing.purchase(seeded, None, eid, 1, "USD")) == purchasing.NOT_AUTHENTICATED
    assert seeded.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert inventory.available(seeded, eid) == 5


# ---- auditing ------------------------------------------------------------- #
def test_every_attempt_is_audited_with_its_reason(seeded, buyer):
    eid = make_event(seeded, capacity=1)
    purchasing.purchase(seeded, buyer, eid, 1, "USD")                                   # success
    for args in [(eid, 1, "USD"), (eid, 0, "USD"), (eid, 1, "XXX"), (999, 1, "USD")]:  # 4 failures
        with pytest.raises(PurchaseError):
            purchasing.purchase(seeded, buyer, *args)
    with pytest.raises(PurchaseError):
        purchasing.purchase(seeded, None, eid, 1, "USD")
    log = list(reversed(attempts(seeded)))
    assert [r.outcome for r in log] == ["success"] + ["fail"] * 5
    assert [r.reason_code for r in log[1:]] == [
        "SOLD_OUT", "INVALID_QUANTITY", "SOLD_OUT", "EVENT_NOT_FOUND", "NOT_AUTHENTICATED"]
    assert all(r.occurred_at for r in log) and log[1].user_email == buyer.email


def test_audit_records_raw_input_for_invalid_attempts(seeded, buyer):
    eid = make_event(seeded)
    with pytest.raises(PurchaseError):
        purchasing.purchase(seeded, buyer, eid, "-7", "zzz")
    r = attempts(seeded)[0]
    assert (r.quantity, r.currency, r.outcome) == ("-7", "zzz", "fail")


def test_payment_decline_rolls_back_and_is_audited(seeded, buyer):
    eid = make_event(seeded, capacity=4)
    with pytest.raises(PurchaseError) as err:
        purchasing.purchase(seeded, buyer, eid, 2, "USD", payment=lambda *a: False)
    assert err.value.code == purchasing.PAYMENT_DECLINED
    assert inventory.available(seeded, eid) == 4
    assert seeded.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert attempts(seeded)[0].reason_code == "PAYMENT_DECLINED"


def test_unexpected_error_rolls_back_everything_and_is_audited(seeded, buyer):
    eid = make_event(seeded, capacity=4)

    def explode(*a):
        raise RuntimeError("payment gateway on fire")

    with pytest.raises(PurchaseError) as err:
        purchasing.purchase(seeded, buyer, eid, 2, "USD", payment=explode)
    assert err.value.code == purchasing.INTERNAL_ERROR
    assert inventory.available(seeded, eid) == 4
    assert attempts(seeded)[0].reason_code == "INTERNAL_ERROR"
    assert [r.outcome for r in attempts(seeded)] == ["fail"]  # no success row leaked


# ---- checkout preview / abandonment -------------------------------------- #
def test_preview_matches_purchase_and_writes_nothing(seeded, student):
    eid = make_event(seeded, capacity=5, price_cents=2500)
    preview = purchasing.preview_checkout(seeded, student, eid, "3", "GBP")
    assert inventory.available(seeded, eid) == 5                      # no hold
    assert seeded.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert attempts(seeded) == []
    order = purchasing.purchase(seeded, student, eid, 3, "GBP")
    assert preview.quote.total_minor == order.total_minor


def test_abandoned_checkout_leaves_data_untouched(seeded, buyer):
    eid = make_event(seeded, capacity=5)
    for _ in range(3):
        purchasing.preview_checkout(seeded, buyer, eid, 2, "USD")     # user walks away
    assert inventory.available(seeded, eid) == 5
    assert purchasing.purchase(seeded, buyer, eid, 5, "USD").quantity == 5  # full stock still buyable


def test_preview_validates_like_purchase(seeded, buyer):
    eid = make_event(seeded)
    assert fail_code(lambda: purchasing.preview_checkout(seeded, buyer, eid, 0, "USD")) == "INVALID_QUANTITY"
    assert fail_code(lambda: purchasing.preview_checkout(seeded, buyer, eid, 1, "NOPE")) == "UNSUPPORTED_CURRENCY"
    assert fail_code(lambda: purchasing.preview_checkout(seeded, None, eid, 1, "USD")) == "NOT_AUTHENTICATED"


# ---- orders --------------------------------------------------------------- #
def test_history_is_per_user_newest_first_and_private(seeded, buyer, student):
    eid = make_event(seeded, capacity=9)
    a = purchasing.purchase(seeded, buyer, eid, 1, "USD")
    b = purchasing.purchase(seeded, buyer, eid, 2, "JPY")
    c = purchasing.purchase(seeded, student, eid, 1, "USD")
    assert [o.id for o in purchasing.list_orders(seeded, buyer)] == [b.id, a.id]
    assert purchasing.get_order(seeded, buyer, c.id) is None           # someone else's order
    assert purchasing.get_order(seeded, buyer, "abc") is None
    assert purchasing.get_order(seeded, buyer, 9999) is None


def test_order_has_confirmation_fields(seeded, buyer):
    eid = make_event(seeded, price_cents=7000)
    o = purchasing.purchase(seeded, buyer, eid, 2, "JPY")
    assert o.event_name == "Test Show" and o.quantity == 2 and o.currency == "JPY"
    assert o.exchange_rate == 150 and o.total_display == "21,000 JPY"


def test_orders_require_login(seeded):
    assert fail_code(lambda: purchasing.list_orders(seeded, None)) == purchasing.NOT_AUTHENTICATED
    assert fail_code(lambda: purchasing.get_order(seeded, None, 1)) == purchasing.NOT_AUTHENTICATED


# ---- concurrency ---------------------------------------------------------- #
def test_concurrent_buyers_never_oversell(db_path):
    setup = database.connect(db_path)
    database.init_db(setup)
    pricing.load_rate_seed(setup, __import__("conftest").RATE_SEED)
    user = identity.register_user(setup, "C", "c@example.com", "longenough1")
    eid = make_event(setup, capacity=5)
    setup.close()

    results, lock, barrier = [], threading.Lock(), threading.Barrier(20)

    def worker():
        conn = database.connect(db_path)
        try:
            barrier.wait()
            try:
                purchasing.purchase(conn, user, eid, 1, "USD")
                outcome = "ok"
            except PurchaseError as exc:
                outcome = exc.code
        finally:
            conn.close()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    check = database.connect(db_path)
    assert results.count("ok") == 5
    assert all(r in ("ok", "SOLD_OUT", "INSUFFICIENT_AVAILABILITY") for r in results)
    assert inventory.available(check, eid) == 0
    assert check.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 5
    assert len(audit.query(check, limit=500)) == 20                    # every attempt logged
    check.close()
