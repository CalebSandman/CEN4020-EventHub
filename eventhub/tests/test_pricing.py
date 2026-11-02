from decimal import Decimal

import pytest

from eventhub import pricing
from eventhub.pricing import PricingError, UnsupportedCurrencyError


@pytest.mark.parametrize("email,expected", [
    ("stu@usf.edu", True),
    ("UPPERCASE@USF.EDU", True),
    ("  Mixed@Usf.Edu  ", True),
    ("name+party@usf.edu", True),
    ("x@mail.usf.edu", False),
    ("x@usf.edu.evil.com", False),
    ("x@notusf.edu", False),
    ("x@usf.com", False),
    ("@usf.edu", False),
    ("a@b@usf.edu", False),
    ("", False),
    (None, False),
])
def test_discount_eligibility(email, expected):
    assert pricing.is_discount_eligible(email) is expected


def test_supported_currencies_come_from_database(seeded):
    assert set(pricing.supported_currencies(seeded)) == {"USD", "EUR", "GBP", "CAD", "MXN", "JPY", "KWD"}
    assert pricing.is_supported(seeded, " eur ")
    assert not pricing.is_supported(seeded, "XXX")
    assert not pricing.is_supported(seeded, "")


def test_usd_no_discount(seeded):
    q = pricing.calculate_price(seeded, 8900, 3, False, "USD")
    assert (q.total_minor, q.unit_minor, q.decimals) == (26700, 8900, 2)
    assert not q.discount_applied


def test_conversion_and_rounding_half_up(seeded):
    # 55.50 USD * 0.92 = 51.06 EUR exactly
    assert pricing.calculate_price(seeded, 5550, 1, False, "EUR").total_minor == 5106
    # 0.01 USD * 0.92 = 0.0092 -> 0.01 ; 0.50*0.92=0.46 ; check half-up: 29.00*0.79*... 
    seeded.execute("UPDATE exchange_rates SET rate='0.5' WHERE currency='EUR'")
    assert pricing.calculate_price(seeded, 1, 1, False, "EUR").total_minor == 1   # 0.005 -> 0.01
    assert pricing.calculate_price(seeded, 3, 1, False, "EUR").total_minor == 2   # 0.015 -> 0.02


def test_zero_decimal_currency(seeded):
    q = pricing.calculate_price(seeded, 7000, 2, False, "JPY")  # 140.00 USD * 150 = 21000 yen
    assert (q.total_minor, q.decimals) == (21000, 0)
    assert pricing.format_money(q.total_minor, "JPY", q.decimals) == "21,000 JPY"


def test_three_decimal_currency(seeded):
    q = pricing.calculate_price(seeded, 10000, 1, False, "KWD")  # 100 * 0.307 = 30.700
    assert (q.total_minor, q.decimals) == (30700, 3)
    assert pricing.format_money(q.total_minor, "KWD", 3) == "30.700 KWD"


def test_student_discount_applied_before_conversion(seeded):
    q = pricing.calculate_price(seeded, 10000, 2, True, "USD")
    expected = int(Decimal(20000) * (100 - pricing.STUDENT_DISCOUNT_PERCENT) / 100)
    assert q.total_minor == expected and q.discount_applied
    assert q.discount_percent == pricing.STUDENT_DISCOUNT_PERCENT


def test_total_is_rounded_once_not_per_ticket(seeded):
    seeded.execute("UPDATE exchange_rates SET rate='0.333' WHERE currency='EUR'")
    q = pricing.calculate_price(seeded, 100, 3, False, "EUR")  # 3.00*0.333 = 0.999 -> 1.00
    assert q.total_minor == 100
    assert q.unit_minor * 3 == 99  # rounding unit-then-multiply would have been wrong


def test_currency_input_normalised(seeded):
    assert pricing.calculate_price(seeded, 1000, 1, False, " eur ").currency == "EUR"


def test_unsupported_currency_rejected(seeded):
    with pytest.raises(UnsupportedCurrencyError):
        pricing.calculate_price(seeded, 1000, 1, False, "XXX")
    with pytest.raises(UnsupportedCurrencyError):
        pricing.calculate_price(seeded, 1000, 1, False, "")


@pytest.mark.parametrize("qty", [0, -1, "2", 1.5, True, None])
def test_bad_quantity_rejected(seeded, qty):
    with pytest.raises(PricingError):
        pricing.calculate_price(seeded, 1000, qty, False, "USD")


@pytest.mark.parametrize("base", [0, -5, 10.5, "100", None])
def test_bad_base_price_rejected(seeded, base):
    with pytest.raises(PricingError):
        pricing.calculate_price(seeded, base, 1, False, "USD")


def test_rate_seed_keeps_admin_edits(seeded):
    from conftest import RATE_SEED
    seeded.execute("UPDATE exchange_rates SET rate='9.99' WHERE currency='EUR'")
    assert pricing.load_rate_seed(seeded, RATE_SEED) == 0
    assert pricing.load_currencies(seeded)["EUR"].rate == Decimal("9.99")


def test_rate_seed_rejects_bad_usd(conn, tmp_path):
    import json
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"currencies": [{"code": "USD", "rate": "2", "decimals": 2}]}))
    with pytest.raises(ValueError):
        pricing.load_rate_seed(conn, p)


def test_no_floats_in_money_path(seeded):
    q = pricing.calculate_price(seeded, 1999, 3, True, "GBP")
    assert isinstance(q.total_minor, int) and isinstance(q.exchange_rate, Decimal)
