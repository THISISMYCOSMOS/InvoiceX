"""Exact USDC amount helpers shared by pricing, persistence, and Solana flows."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import Field, PlainSerializer

USDC_DECIMALS = 6
USDC_SCALE_INT = 10**USDC_DECIMALS
USDC_SCALE = Decimal(USDC_SCALE_INT)
USDC_QUANTUM = Decimal("0.000001")

# Public JSON keeps the existing numeric `...Usdc` contract. Authoritative
# calculations and blockchain execution use the accompanying base-unit value.
UsdcAmount = Annotated[
    Decimal,
    Field(decimal_places=USDC_DECIMALS, allow_inf_nan=False),
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]


def parse_usdc(value: object, *, allow_zero: bool = False) -> Decimal:
    """Parse an exact USDC amount without rounding or binary floats."""

    if isinstance(value, bool):
        raise ValueError("boolean is not a USDC amount")
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, ValueError) as exc:
        raise ValueError("invalid USDC amount") from exc
    if not amount.is_finite() or amount < 0 or (amount == 0 and not allow_zero):
        raise ValueError("USDC amount must be positive and finite")
    exponent = amount.as_tuple().exponent
    if exponent < -USDC_DECIMALS:
        raise ValueError("USDC supports at most six decimal places")
    return amount.quantize(USDC_QUANTUM)


def usdc_to_base_units(value: object, *, allow_zero: bool = False) -> int:
    amount = parse_usdc(value, allow_zero=allow_zero)
    return int(amount * USDC_SCALE)


def base_units_to_usdc(value: int | str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not a base-unit amount")
    try:
        units = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid USDC base-unit amount") from exc
    if units < 0:
        raise ValueError("USDC base-unit amount cannot be negative")
    return (Decimal(units) / USDC_SCALE).quantize(USDC_QUANTUM)


def base_units_string(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("invalid USDC base-unit amount")
    return str(value)
