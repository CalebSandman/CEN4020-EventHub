"""Generic input hygiene for the HTTP boundary (system-001).

Domain rules (quantity range, supported currencies, rate format) are enforced
by the owning components; this module only bounds and cleans raw form text so
nothing oversized or control-character-laden travels inward.
"""
from __future__ import annotations


def clean_text(raw, max_len: int) -> str:
    """Trim, drop control characters and truncate to ``max_len``."""
    text = "" if raw is None else str(raw)
    text = "".join(ch for ch in text if ch.isprintable())
    return text.strip()[:max_len]
