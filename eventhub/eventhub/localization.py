"""Presentation-only translation and regional formatting.

Amounts enter as integer currency minor units. This module never converts rates
or changes stored values. Add a locale by registering its resource and patterns.
"""
import json
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

RESOURCES = Path(__file__).with_name("locales")
LOCALES = {"en_US": "English", "es_ES": "Español"}
DATE_PATTERNS = {"en_US": "%m/%d/%Y %I:%M %p", "es_ES": "%d/%m/%Y %H:%M"}
SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CAD": "CA$", "MXN": "MX$", "KWD": "KD"}


def normalize_locale(value):
    return value if value in LOCALES else "en_US"


@lru_cache(maxsize=8)
def _messages(locale):
    path = RESOURCES / f"{locale}.json"
    translations = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    errors = RESOURCES / f"{locale}_errors.json"
    if errors.exists():
        translations.update(json.loads(errors.read_text(encoding="utf-8")))
    return translations


def translate(message, locale="en_US"):
    """English source text is the key; absent translations fall back to it."""
    if locale == "en_US":
        return message
    return _messages(normalize_locale(locale)).get(message, message)


def format_date(value, locale="en_US"):
    try:
        moment = datetime.fromisoformat(value)
        return moment.strftime(DATE_PATTERNS[normalize_locale(locale)])
    except (TypeError, ValueError):
        return str(value)


def format_money(minor, currency, decimals, locale="en_US"):
    """Display only: scale by the currency's stored precision, never by 100."""
    if not isinstance(minor, int) or isinstance(minor, bool) or decimals not in range(5):
        raise ValueError("invalid minor amount or currency precision")
    major = Decimal(minor).scaleb(-decimals)
    number = f"{major:,.{decimals}f}"
    code = str(currency).upper()
    symbol = SYMBOLS.get(code, code)
    if normalize_locale(locale) == "es_ES":
        number = number.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
        return f"{number} {symbol} {code}"
    return f"{symbol}{number} {code}"
