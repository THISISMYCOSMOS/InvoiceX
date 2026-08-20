"""Exact MVP pricing for eligible InvoiceX invoice RWAs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from invoicex_backend.money import USDC_SCALE, base_units_to_usdc

Rate = Decimal
_BPS_DENOMINATOR = Decimal(10_000)
_DAYS_PER_YEAR = Decimal(365)


def bps_to_fraction(bps: int) -> Rate:
    return Decimal(bps) / _BPS_DENOMINATOR


def fraction_to_bps(rate: Rate) -> int:
    return int((rate * _BPS_DENOMINATOR).to_integral_value(rounding=ROUND_HALF_UP))


@dataclass(frozen=True, slots=True)
class PricingPolicy:
    sofr_bps: int | None = 362
    sofr_as_of: str | None = "2026-08-14"
    sofr_source: str | None = "Federal Reserve Bank of New York"
    risk_spreads_bps: tuple[tuple[int, int], ...] = (
        (90, 100),
        (80, 175),
        (70, 300),
    )
    country_legal_spread_bps: int = 50
    platform_fee_share_bps: int = 1_000

    def is_configured(self) -> bool:
        return (
            isinstance(self.sofr_bps, int)
            and not isinstance(self.sofr_bps, bool)
            and 0 <= self.sofr_bps <= 10_000
            and bool(self.sofr_as_of and self.sofr_as_of.strip())
            and bool(self.sofr_source and self.sofr_source.strip())
        )

    @property
    def platform_fee_share(self) -> Rate:
        return bps_to_fraction(self.platform_fee_share_bps)

    def risk_spread_bps(self, score: int) -> int | None:
        return next((spread for minimum, spread in self.risk_spreads_bps if score >= minimum), None)


@dataclass(frozen=True, slots=True)
class DynamicPricing:
    face_value_base_units: int
    remaining_term_days: int
    sofr_bps: int
    sofr_as_of: str
    sofr_source: str
    buyer_risk_score: int
    buyer_risk_spread_bps: int
    country_legal_spread_bps: int
    investor_net_annual_yield_bps: int
    platform_fee_share_bps: int
    purchase_amount_base_units: int
    supplier_settlement_base_units: int
    investor_net_return_base_units: int
    platform_fee_base_units: int

    @property
    def face_value_usdc(self) -> Decimal:
        return base_units_to_usdc(self.face_value_base_units)

    @property
    def purchase_amount_usdc(self) -> Decimal:
        return base_units_to_usdc(self.purchase_amount_base_units)

    @property
    def supplier_settlement_amount_usdc(self) -> Decimal:
        return base_units_to_usdc(self.supplier_settlement_base_units)

    @property
    def investor_net_return_usdc(self) -> Decimal:
        return base_units_to_usdc(self.investor_net_return_base_units)

    @property
    def platform_fee_usdc(self) -> Decimal:
        return base_units_to_usdc(self.platform_fee_base_units)

    @property
    def investor_settlement_base_units(self) -> int:
        return self.purchase_amount_base_units + self.investor_net_return_base_units

    @property
    def investor_settlement_usdc(self) -> Decimal:
        return base_units_to_usdc(self.investor_settlement_base_units)

    @property
    def supplier_expected_settlement_usdc(self) -> Decimal:
        return self.supplier_settlement_amount_usdc

    @property
    def expected_investor_return_usdc(self) -> Decimal:
        return self.investor_net_return_usdc

    @property
    def investor_net_annual_yield(self) -> Rate:
        return bps_to_fraction(self.investor_net_annual_yield_bps)


def _round_base_units(exact_usdc: Decimal) -> int:
    return int((exact_usdc * USDC_SCALE).to_integral_value(rounding=ROUND_HALF_UP))


def calculate_dynamic_pricing(
    *,
    face_value_base_units: int,
    remaining_term_days: int,
    risk_score: int | None,
    policy: PricingPolicy,
) -> DynamicPricing | None:
    """Apply the closed-form policy and reconcile only micro-USDC rounding.

    R and Fee are rounded independently to the USDC token precision. The
    remaining base units are assigned to P, guaranteeing the stored accounting
    identity and all subsequent on-chain transfers use exactly the same values.
    """

    if (
        not isinstance(face_value_base_units, int)
        or isinstance(face_value_base_units, bool)
        or face_value_base_units <= 0
        or not isinstance(remaining_term_days, int)
        or isinstance(remaining_term_days, bool)
        or remaining_term_days <= 0
        or risk_score is None
        or not isinstance(risk_score, int)
        or isinstance(risk_score, bool)
        or not 0 <= risk_score <= 100
        or not policy.is_configured()
    ):
        return None
    risk_spread_bps = policy.risk_spread_bps(risk_score)
    if risk_spread_bps is None:
        return None

    try:
        annual_yield_bps = policy.sofr_bps + risk_spread_bps + policy.country_legal_spread_bps
        annual_yield = bps_to_fraction(annual_yield_bps)
        term = Decimal(remaining_term_days) / _DAYS_PER_YEAR
        face_value = Decimal(face_value_base_units) / USDC_SCALE
        exact_purchase = face_value / (
            Decimal(1) + annual_yield * term * (Decimal(1) + policy.platform_fee_share)
        )
        exact_return = exact_purchase * annual_yield * term
        exact_fee = exact_return * policy.platform_fee_share
        # A valid priced RWA must retain both economic legs even for a very
        # small face value.  One micro-USDC is the minimum representable unit.
        investor_return_units = max(1, _round_base_units(exact_return))
        platform_fee_units = max(1, _round_base_units(exact_fee))
        purchase_units = face_value_base_units - investor_return_units - platform_fee_units
        if purchase_units <= 0:
            return None
    except (InvalidOperation, TypeError, ValueError, ArithmeticError):
        return None

    return DynamicPricing(
        face_value_base_units=face_value_base_units,
        remaining_term_days=remaining_term_days,
        sofr_bps=policy.sofr_bps,
        sofr_as_of=policy.sofr_as_of.strip(),
        sofr_source=policy.sofr_source.strip(),
        buyer_risk_score=risk_score,
        buyer_risk_spread_bps=risk_spread_bps,
        country_legal_spread_bps=policy.country_legal_spread_bps,
        investor_net_annual_yield_bps=annual_yield_bps,
        platform_fee_share_bps=policy.platform_fee_share_bps,
        purchase_amount_base_units=purchase_units,
        supplier_settlement_base_units=purchase_units,
        investor_net_return_base_units=investor_return_units,
        platform_fee_base_units=platform_fee_units,
    )
