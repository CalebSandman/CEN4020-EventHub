from decimal import Decimal

import pytest

from eventhub import administration, audit, pricing
from eventhub.administration import AdminError, PermissionDenied


def test_buyer_and_anonymous_are_denied_everything(seeded, buyer):
    for actor in (buyer, None):
        with pytest.raises(PermissionDenied):
            administration.list_rates(seeded, actor)
        with pytest.raises(PermissionDenied):
            administration.update_rate(seeded, actor, "EUR", "0.5")
        with pytest.raises(PermissionDenied):
            administration.review_audit(seeded, actor)
    assert pricing.load_currencies(seeded)["EUR"].rate == Decimal("0.92")


def test_admin_updates_rate_and_pricing_uses_it(seeded, admin):
    administration.update_rate(seeded, admin, " eur ", "0.50")
    assert pricing.calculate_price(seeded, 10000, 1, False, "EUR").total_minor == 5000
    row = [r for r in administration.list_rates(seeded, admin) if r["currency"] == "EUR"][0]
    assert row["updated_by"] == admin.id


@pytest.mark.parametrize("bad", ["", "abc", "0", "-1", "NaN", "Infinity", "1e999", "2000000", "0.123456789", "x" * 50, None])
def test_invalid_rates_rejected(seeded, admin, bad):
    with pytest.raises(AdminError) as err:
        administration.update_rate(seeded, admin, "EUR", bad)
    assert err.value.code == "RATE_INVALID"
    assert pricing.load_currencies(seeded)["EUR"].rate == Decimal("0.92")


def test_usd_is_fixed(seeded, admin):
    with pytest.raises(AdminError) as err:
        administration.update_rate(seeded, admin, "USD", "2")
    assert err.value.code == "BASE_CURRENCY"


def test_unknown_currency_cannot_be_added_via_update(seeded, admin):
    with pytest.raises(AdminError) as err:
        administration.update_rate(seeded, admin, "XXX", "1.5")
    assert err.value.code == "UNSUPPORTED_CURRENCY"
    assert not pricing.is_supported(seeded, "XXX")


def test_admin_reviews_audit_records(seeded, admin):
    audit.record(seeded, user_id=1, user_email="a@b.co", event_ref=1, quantity=1, currency="USD", outcome="fail",
                 reason_code="SOLD_OUT")
    audit.record(seeded, user_id=2, user_email="c@d.co", event_ref=1, quantity=1, currency="USD", outcome="success")
    assert len(administration.review_audit(seeded, admin)) == 2
    assert [r.user_email for r in administration.review_audit(seeded, admin, outcome="fail")] == ["a@b.co"]
    assert len(administration.review_audit(seeded, admin, outcome="", user_email="", reason_code="")) == 2
