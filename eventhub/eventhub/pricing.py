"""Pricing component: the ONE place money is computed.

``calculate_price`` takes base price, quantity, discount eligibility and target
currency and returns the amount. Nothing else in the code base multiplies,
discounts, converts or rounds money.

Money representation (see docs/decisions/0001-money-representation.md):
``decimal.Decimal`` for all arithmetic, integer *minor units* (cents, yen,
fils...) for storage and transport, and each currency's own decimal places.
Never ``float``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

BASE_CURRENCY = "USD"

# ############################################################################
# # OPEN QUESTION - NOT A REAL BUSINESS VALUE                                #
# # The student discount percentage has not been provided by the customer.   #
# # 10 is a PLACEHOLDER so the pricing code can be built and tested.         #
# # Replace it as soon as Darnell Washington confirms the number.            #
# # Tracked in docs/open-questions.md (Q1).                                  #
# ############################################################################
STUDENT_DISCOUNT_PERCENT = Decimal("10")

STUDENT_EMAIL_SUFFIX = "@usf.edu"


class PricingError(ValueError):
    pass


class UnsupportedCurrencyError(PricingError):
    pass


# --------------------------------------------------------------------------- #
# Discount eligibility (own small function: Call 4, Kenji's questions)
# --------------------------------------------------------------------------- #
def is_discount_eligible(email) -> bool:
    """True for ``@usf.edu`` addresses (student-discount-001).

    The email is normalised (trimmed, lower-cased) first, so UPPERCASE@USF.EDU
    qualifies. Current answers to the unspecified cases, all decided HERE only:
      * plus-addressing (name+party@usf.edu) -> eligible (still an @usf.edu address)
      * subdomains (x@mail.usf.edu)          -> NOT eligible (not literally @usf.edu)
    No student ID is ever requested (student-discount-002).
    """
    if not isinstance(email, str):
        return False
    normalized = email.strip().lower()
    if not normalized.endswith(STUDENT_EMAIL_SUFFIX):
        return False
    local = normalized[: -len(STUDENT_EMAIL_SUFFIX)]
    return bool(local) and "@" not in local and not any(c.isspace() for c in local)


# --------------------------------------------------------------------------- #
# Exchange rates (stored in the database, seeded from a data file)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CurrencyInfo:
    code: str
    rate: Decimal  # units of this currency per 1 USD
    decimals: int


def normalize_currency(code) -> str:
    return str(code or "").strip().upper()


def load_currencies(conn) -> dict[str, CurrencyInfo]:
    rows = conn.execute("SELECT currency, rate, decimals FROM exchange_rates ORDER BY currency")
    return {r["currency"]: CurrencyInfo(r["currency"], Decimal(r["rate"]), r["decimals"]) for r in rows}


def supported_currencies(conn) -> list[str]:
    return list(load_currencies(conn))


def is_supported(conn, code) -> bool:
    return normalize_currency(code) in load_currencies(conn)


def load_rate_seed(conn, path) -> int:
    """Import initial exchange rates; existing rows (admin edits) are kept."""
    from . import database  # local import keeps module import-light

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    now = database.to_iso(database.utcnow())
    added = 0
    for item in data["currencies"]:
        code = normalize_currency(item["code"])
        rate = Decimal(str(item["rate"]))
        decimals = int(item["decimals"])
        if not rate.is_finite() or rate <= 0:
            raise ValueError(f"invalid rate for {code}")
        if code == BASE_CURRENCY and rate != 1:
            raise ValueError("USD rate must be exactly 1")
        cur = conn.execute(
            "INSERT OR IGNORE INTO exchange_rates (currency, rate, decimals, updated_at) "
            "VALUES (?,?,?,?)",
            (code, format(rate, "f"), decimals, now),
        )
        added += cur.rowcount
    return added


# --------------------------------------------------------------------------- #
# The pricing function
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PriceQuote:
    currency: str
    exchange_rate: Decimal
    decimals: int
    quantity: int
    unit_minor: int            # list price of one ticket in `currency` (before discount)
    total_minor: int           # amount to pay in `currency`, rounded once
    discount_percent: Decimal  # 0 when no discount applied

    @property
    def discount_applied(self) -> bool:
        return self.discount_percent > 0


def _to_minor(amount: Decimal, decimals: int) -> int:
    quantum = Decimal(1).scaleb(-decimals)
    return int(amount.quantize(quantum, rounding=ROUND_HALF_UP).scaleb(decimals))


def calculate_price(conn, base_price_cents: int, quantity: int,
                    discount_eligible: bool, currency: str) -> PriceQuote:
    """Return the authoritative price.

    total = base_usd * quantity * (1 - discount%) * rate, rounded ONCE to the
    currency's own precision (half-up). The exact total is rounded, not
    unit-price x quantity, so rounding error never compounds.
    """
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise PricingError("quantity must be a positive integer")
    if isinstance(base_price_cents, bool) or not isinstance(base_price_cents, int) or base_price_cents <= 0:
        raise PricingError("base price must be a positive integer number of cents")
    code = normalize_currency(currency)
    info = load_currencies(conn).get(code)
    if info is None:
        raise UnsupportedCurrencyError(f"unsupported currency: {code or '(blank)'}")

    base_usd = Decimal(base_price_cents) / Decimal(100)
    percent = STUDENT_DISCOUNT_PERCENT if discount_eligible else Decimal(0)
    net_usd = base_usd * quantity * (Decimal(100) - percent) / Decimal(100)
    return PriceQuote(
        currency=code,
        exchange_rate=info.rate,
        decimals=info.decimals,
        quantity=quantity,
        unit_minor=_to_minor(base_usd * info.rate, info.decimals),
        total_minor=_to_minor(net_usd * info.rate, info.decimals),
        discount_percent=percent,
    )


def format_money(minor: int, currency: str, decimals: int) -> str:
    """Render minor units for display, e.g. ``1,234.50 EUR`` / ``5,000 JPY``."""
    major = Decimal(int(minor)).scaleb(-decimals)
    return f"{major:,.{decimals}f} {currency}"
