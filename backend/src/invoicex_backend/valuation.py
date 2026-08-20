"""Deterministic invoice valuation for USDC-denominated RWA issuance."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from invoicex_backend.money import base_units_to_usdc, usdc_to_base_units


@dataclass(frozen=True, slots=True)
class UsdcValuation:
    face_value_base_units: int
    source_currency_to_usdc_rate: Decimal

    @property
    def face_value_usdc(self) -> Decimal:
        return base_units_to_usdc(self.face_value_base_units)


def value_invoice_in_usdc(*, invoice_amount: object, currency: str) -> UsdcValuation:
    """Quote an invoice's face value in USDC without inventing FX rates.

    The MVP supports USD and USDC invoices at their 1:1 peg. Other currencies
    need a persisted partner FX quote before they can back an RWA position.
    """

    normalized_currency = currency.strip().upper()
    if normalized_currency not in {"USD", "USDC"}:
        raise ValueError(f"Unsupported RWA valuation currency: {normalized_currency}")
    return UsdcValuation(
        face_value_base_units=usdc_to_base_units(invoice_amount),
        source_currency_to_usdc_rate=Decimal(1),
    )
