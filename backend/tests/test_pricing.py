from __future__ import annotations

from decimal import Decimal

import pytest

from invoicex_backend.pricing import PricingPolicy, calculate_dynamic_pricing

POLICY = PricingPolicy(
    sofr_bps=362,
    sofr_as_of="2026-08-14",
    sofr_source="Federal Reserve Bank of New York",
)


@pytest.mark.parametrize(
    ("score", "expected_spread_bps"),
    [(95, 100), (90, 100), (89, 175), (86, 175), (80, 175), (79, 300), (70, 300)],
)
def test_buyer_risk_spread_policy(score: int, expected_spread_bps: int) -> None:
    pricing = calculate_dynamic_pricing(
        face_value_base_units=96_000_000_000,
        remaining_term_days=90,
        risk_score=score,
        policy=POLICY,
    )

    assert pricing is not None
    assert pricing.buyer_risk_spread_bps == expected_spread_bps
    assert pricing.country_legal_spread_bps == 50


def test_dynamic_pricing_uses_the_closed_form_mvp_policy() -> None:
    pricing = calculate_dynamic_pricing(
        face_value_base_units=5_000_000,
        remaining_term_days=90,
        risk_score=86,
        policy=POLICY,
    )

    assert pricing is not None
    assert pricing.sofr_bps == 362
    assert pricing.sofr_as_of == "2026-08-14"
    assert pricing.sofr_source == "Federal Reserve Bank of New York"
    assert pricing.buyer_risk_score == 86
    assert pricing.buyer_risk_spread_bps == 175
    assert pricing.country_legal_spread_bps == 50
    assert pricing.investor_net_annual_yield_bps == 587
    assert pricing.investor_net_annual_yield == Decimal("0.0587")
    assert pricing.purchase_amount_base_units == 4_921_640
    assert pricing.investor_net_return_base_units == 71_236
    assert pricing.platform_fee_base_units == 7_124
    assert pricing.purchase_amount_usdc == Decimal("4.921640")
    assert pricing.supplier_settlement_amount_usdc == Decimal("4.921640")
    assert pricing.investor_net_return_usdc == Decimal("0.071236")
    assert pricing.platform_fee_share_bps == 1_000
    assert pricing.platform_fee_usdc == Decimal("0.007124")
    assert pricing.investor_settlement_base_units == 4_992_876
    assert pricing.investor_settlement_usdc == Decimal("4.992876")
    assert (
        pricing.purchase_amount_base_units
        + pricing.investor_net_return_base_units
        + pricing.platform_fee_base_units
        == pricing.face_value_base_units
    )


def test_integer_usdc_rounding_preserves_the_accounting_identity() -> None:
    pricing = calculate_dynamic_pricing(
        face_value_base_units=7,
        remaining_term_days=365,
        risk_score=70,
        policy=POLICY,
    )

    assert pricing is not None
    assert (
        pricing.purchase_amount_base_units
        + pricing.investor_net_return_base_units
        + pricing.platform_fee_base_units
        == 7
    )
    assert pricing.investor_net_return_base_units >= 1
    assert pricing.platform_fee_base_units >= 1


@pytest.mark.parametrize("score", [0, 50, 69])
def test_dynamic_pricing_excludes_scores_below_seventy(score: int) -> None:
    assert calculate_dynamic_pricing(
        face_value_base_units=10_000,
        remaining_term_days=30,
        risk_score=score,
        policy=POLICY,
    ) is None


@pytest.mark.parametrize(
    ("face_value_base_units", "remaining_term_days", "risk_score", "policy"),
    [
        (0, 30, 86, POLICY),
        (10_000, 0, 86, POLICY),
        (10_000, 30, None, POLICY),
        (10_000, 30, 86, PricingPolicy(sofr_bps=None, sofr_as_of=None, sofr_source=None)),
        (
            10_000,
            30,
            86,
            PricingPolicy(sofr_bps="invalid", sofr_as_of="2026-08-14", sofr_source="Federal Reserve Bank of New York"),  # type: ignore[arg-type]
        ),
    ],
)
def test_dynamic_pricing_is_unavailable_for_missing_or_invalid_inputs(
    face_value_base_units: int,
    remaining_term_days: int,
    risk_score: int | None,
    policy: PricingPolicy,
) -> None:
    assert calculate_dynamic_pricing(
        face_value_base_units=face_value_base_units,
        remaining_term_days=remaining_term_days,
        risk_score=risk_score,
        policy=policy,
    ) is None
