"""Small, reusable cleaning functions. Tested in tests/test_cleaning.py"""

from __future__ import annotations

import re

MEMBER_MIN, MEMBER_MAX = 10001, 99999


def normalize_member_number(raw) -> int | None:
    """Turn messy member numbers into a clean int, or None if it can't be one.

    '00048213' -> 48213, '48,213' -> 48213, '#48213' -> 48213, ' 48213 ' -> 48213
    '', None, 'test', '000000000' -> None
    """
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw)) # keep only 0-9
    if not digits:
        return None
    number = int(digits)
    if not MEMBER_MIN <= number <= MEMBER_MAX:
        return None
    return number


def parse_amount(raw) -> float | None:
    """'$1,234.50' -> 1234.5, '(45.00)' -> -45.0, 'n/a' -> None, 12.5 -> 12.5"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace("$", "").replace(",", "").strip()
    try:
        value = float(text)
    except ValueError:
        return None
    return -value if negative else value


def clean_whitespace(text: str | None) -> str | None:
    """Collapse runs of spaces/newlines to one space and trim the ends."""
    if text is None:
        return None
    return re.sub(r"\s+", " ", text).strip()