import pytest

from kvcu.cleaning import clean_whitespace, normalize_member_number, parse_amount


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("00048213", 48213),
        ("48,213", 48213),
        ("#48213", 48213),
        ("  48213  ", 48213),
        ("", None),
        ("test", None),
        ("000000000", None),
    ],
)
def test_normalize_member_number(raw, expected):
    assert normalize_member_number(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("$1,234.50", 1234.5),
        ("1234.5", 1234.5),
        ("(45.00)", -45.0),
        ("n/a", None),
        (12.5, 12.5),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


def test_clean_whitespace():
    assert clean_whitespace("  too  many\n spaces ") == "too many spaces"
    