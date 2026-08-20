from __future__ import annotations

from decimal import Decimal

import pytest

from invoicex_backend.money import base_units_to_usdc, parse_usdc, usdc_to_base_units


@pytest.mark.parametrize(
    ("raw", "expected", "base_units"),
    [
        ("5", Decimal("5.000000"), 5_000_000),
        ("5.25", Decimal("5.250000"), 5_250_000),
        ("5.000001", Decimal("5.000001"), 5_000_001),
    ],
)
def test_usdc_parser_preserves_all_six_decimals(
    raw: str, expected: Decimal, base_units: int
) -> None:
    assert parse_usdc(raw) == expected
    assert usdc_to_base_units(raw) == base_units
    assert base_units_to_usdc(base_units) == expected


@pytest.mark.parametrize("raw", ["5.0000001", "NaN", "Infinity", "0", "-1"])
def test_usdc_parser_rejects_invalid_amounts(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_usdc(raw)
