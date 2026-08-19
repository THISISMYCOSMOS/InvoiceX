"""Deterministic invoice valuation for USDC-denominated RWA issuance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UsdcValuation:
    face_value_usdc: int
    source_currency_to_usdc_rate: float


def value_invoice_in_usdc(*, invoice_amount: int, currency: str) -> UsdcValuation:
    """Quote an invoice's face value in USDC without inventing FX rates.

    The MVP supports USD and USDC invoices at their 1:1 peg. Other currencies
    need a persisted partner FX quote before they can back an RWA position.
    """

    normalized_currency = currency.strip().upper()
    if normalized_currency not in {"USD", "USDC"}:
        raise ValueError(f"Unsupported RWA valuation currency: {normalized_currency}")
    return UsdcValuation(
        face_value_usdc=invoice_amount,
        source_currency_to_usdc_rate=1.0,
    )
