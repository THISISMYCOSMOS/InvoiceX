"""Transparent dynamic pricing for eligible invoice RWAs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP


Rate = Decimal


def fraction_to_bps(rate: Rate) -> int:
    """Convert a decimal-fraction rate to an integer API basis-point value."""

    return int((rate * Decimal(10_000)).to_integral_value(rounding=ROUND_HALF_UP))


@dataclass(frozen=True, slots=True)
class PricingPolicy:
    sofr_rate: Rate = Decimal("0.05")
    risk_spreads: tuple[tuple[int, Rate], ...] = (
        (90, Decimal("0.015")),
        (80, Decimal("0.025")),
        (70, Decimal("0.04")),
    )
    country_spreads: tuple[tuple[str, Rate], ...] = (
        ("LOW", Decimal("0.005")),
        ("MEDIUM", Decimal("0.015")),
        ("HIGH", Decimal("0.03")),
    )
    platform_fee_rate: Rate = Decimal("0.012")

    def risk_spread(self, score: int) -> Rate | None:
        return next((spread for minimum, spread in self.risk_spreads if score >= minimum), None)

    def country_spread(self, tier: str) -> Rate:
        normalized = tier.strip().upper()
        return dict(self.country_spreads).get(normalized, dict(self.country_spreads)["MEDIUM"])


@dataclass(frozen=True, slots=True)
class DynamicPricing:
    face_value_usdc: int
    remaining_term_days: int
    sofr_rate: Rate
    risk_spread: Rate
    country_legal_spread: Rate
    annual_expected_yield: Rate
    expected_investor_return_usdc: int
    purchase_amount_usdc: int
    platform_fee_usdc: int
    supplier_expected_settlement_usdc: int


def calculate_dynamic_pricing(
    *,
    face_value_usdc: int,
    remaining_term_days: int,
    risk_score: int,
    country_risk_tier: str,
    policy: PricingPolicy,
) -> DynamicPricing | None:
    if face_value_usdc < 0 or remaining_term_days < 0:
        raise ValueError("Pricing values cannot be negative")
    risk_spread = policy.risk_spread(risk_score)
    if risk_spread is None:
        return None
    country_spread = policy.country_spread(country_risk_tier)
    annual_yield = policy.sofr_rate + risk_spread + country_spread
    expected_return = int(
        (
            Decimal(face_value_usdc)
            * annual_yield
            * Decimal(remaining_term_days)
            / Decimal(365)
        ).to_integral_value(rounding=ROUND_FLOOR)
    )
    expected_return = min(face_value_usdc, expected_return)
    purchase_amount = face_value_usdc - expected_return
    platform_fee = int(
        (Decimal(face_value_usdc) * policy.platform_fee_rate).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    supplier_settlement = max(0, purchase_amount - platform_fee)
    return DynamicPricing(
        face_value_usdc=face_value_usdc,
        remaining_term_days=remaining_term_days,
        sofr_rate=policy.sofr_rate,
        risk_spread=risk_spread,
        country_legal_spread=country_spread,
        annual_expected_yield=annual_yield,
        expected_investor_return_usdc=expected_return,
        purchase_amount_usdc=purchase_amount,
        platform_fee_usdc=platform_fee,
        supplier_expected_settlement_usdc=supplier_settlement,
    )
