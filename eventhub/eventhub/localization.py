"""Presentation-only translation and regional formatting.

Amounts enter as integer currency minor units. This module never converts rates
or changes stored values. Add a locale by registering its resource and patterns.
"""
import json
import re
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

RESOURCES = Path(__file__).with_name("locales")
LOCALES = {"en_US": "English", "es_ES": "Español"}
DATE_PATTERNS = {"en_US": "%m/%d/%Y %I:%M %p", "es_ES": "%d/%m/%Y %H:%M"}
SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CAD": "CA$", "MXN": "MX$", "KWD": "KD"}

# Numeric service errors keep their English source text and audit codes. Only
# the rendered message is translated, so callers do not depend on a locale.
_SPANISH_PATTERNS = (
    (re.compile(r"Name must be at most (\d+) characters\."),
     "El nombre debe tener como máximo {0} caracteres."),
    (re.compile(r"Password must be at least (\d+) characters\."),
     "La contraseña debe tener al menos {0} caracteres."),
    (re.compile(r"Password must be at most (\d+) characters\."),
     "La contraseña debe tener como máximo {0} caracteres."),
    (re.compile(r"You can buy at most (\d+) tickets per order\."),
     "Puede comprar como máximo {0} entradas por pedido."),
    (re.compile(r"Only (\d+) ticket\(s\) remain for this event\."),
     "Solo quedan {0} entradas para este evento."),
    (re.compile(r"Tickets became unavailable\. Only (\d+) ticket\(s\) remain\."),
     "Las entradas dejaron de estar disponibles. Solo quedan {0}."),
    (re.compile(r"At most (\d+) decimal places\."),
     "Como máximo {0} decimales."),
)


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
    locale = normalize_locale(locale)
    if locale == "en_US":
        return message
    translated = _messages(locale).get(message)
    if translated is not None:
        return translated
    for pattern, template in _SPANISH_PATTERNS:
        match = pattern.fullmatch(str(message))
        if match:
            return template.format(*match.groups())
    return message


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
