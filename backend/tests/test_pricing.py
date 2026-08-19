from decimal import Decimal

import pytest

from invoicex_backend.pricing import (
    PricingPolicy,
    calculate_dynamic_pricing,
    fraction_to_bps,
)


def test_dynamic_pricing_uses_sofr_spreads_and_remaining_term() -> None:
    pricing = calculate_dynamic_pricing(
        face_value_usdc=96_000,
        remaining_term_days=90,
        risk_score=86,
        country_risk_tier="MEDIUM",
        policy=PricingPolicy(
            sofr_rate=Decimal("0.05"),
            risk_spreads=(
                (90, Decimal("0.015")),
                (80, Decimal("0.025")),
                (70, Decimal("0.04")),
            ),
            country_spreads=(
                ("LOW", Decimal("0.005")),
                ("MEDIUM", Decimal("0.015")),
                ("HIGH", Decimal("0.03")),
            ),
            platform_fee_rate=Decimal("0.012"),
        ),
    )

    assert pricing is not None
    assert pricing.sofr_rate == Decimal("0.05")
    assert pricing.risk_spread == Decimal("0.025")
    assert pricing.country_legal_spread == Decimal("0.015")
    assert pricing.annual_expected_yield == Decimal("0.09")
    assert fraction_to_bps(pricing.annual_expected_yield) == 900
    assert pricing.expected_investor_return_usdc == 2_130
    assert pricing.purchase_amount_usdc == 93_870
    assert pricing.platform_fee_usdc == 1_152
    assert pricing.supplier_expected_settlement_usdc == 92_718


def test_dynamic_pricing_for_invoice_2026_010_inputs_is_finite() -> None:
    pricing = calculate_dynamic_pricing(
        face_value_usdc=96_000,
        remaining_term_days=29,
        risk_score=86,
        country_risk_tier="LOW",
        policy=PricingPolicy(),
    )

    assert pricing is not None
    assert pricing.sofr_rate == Decimal("0.05")
    assert pricing.risk_spread == Decimal("0.025")
    assert pricing.country_legal_spread == Decimal("0.005")
    assert pricing.annual_expected_yield == Decimal("0.08")
    assert pricing.expected_investor_return_usdc == 610
    assert pricing.purchase_amount_usdc == 95_390
    assert pricing.platform_fee_usdc == 1_152
    assert pricing.supplier_expected_settlement_usdc == 94_238


@pytest.mark.parametrize("score", [0, 50, 69])
def test_dynamic_pricing_excludes_scores_below_seventy(score: int) -> None:
    assert calculate_dynamic_pricing(
        face_value_usdc=10_000,
        remaining_term_days=30,
        risk_score=score,
        country_risk_tier="LOW",
        policy=PricingPolicy(),
    ) is None
