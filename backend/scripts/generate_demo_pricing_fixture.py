#!/usr/bin/env python3
"""Generate the frontend demo fixture from the canonical backend pricing code."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from invoicex_backend.money import base_units_to_usdc
from invoicex_backend.pricing import PricingPolicy, calculate_dynamic_pricing

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "frontend/src/mocks/generatedPricingFixture.json"


def fixture() -> dict[str, object]:
    pricing = calculate_dynamic_pricing(
        face_value_base_units=3_000_000,
        remaining_term_days=90,
        risk_score=86,
        policy=PricingPolicy(),
    )
    if pricing is None:  # pragma: no cover - fixed policy invariant
        raise RuntimeError("canonical demo pricing is unavailable")
    discount_base_units = pricing.face_value_base_units - pricing.purchase_amount_base_units
    return {
        "faceValueUsdc": float(pricing.face_value_usdc),
        "faceValueBaseUnits": str(pricing.face_value_base_units),
        "purchaseAmountUsdc": float(pricing.purchase_amount_usdc),
        "purchaseAmountBaseUnits": str(pricing.purchase_amount_base_units),
        "purchaseRateBps": (
            pricing.purchase_amount_base_units * 10_000 // pricing.face_value_base_units
        ),
        "discountAmountUsdc": float(base_units_to_usdc(discount_base_units)),
        "discountRateBps": discount_base_units * 10_000 // pricing.face_value_base_units,
        "supplierSettlementUsdc": float(pricing.supplier_settlement_amount_usdc),
        "supplierSettlementBaseUnits": str(pricing.supplier_settlement_base_units),
        "investorNetReturnUsdc": float(pricing.investor_net_return_usdc),
        "investorNetReturnBaseUnits": str(pricing.investor_net_return_base_units),
        "investorSettlementUsdc": float(pricing.investor_settlement_usdc),
        "investorSettlementBaseUnits": str(pricing.investor_settlement_base_units),
        "platformFeeUsdc": float(pricing.platform_fee_usdc),
        "platformFeeBaseUnits": str(pricing.platform_fee_base_units),
        "remainingTermDays": pricing.remaining_term_days,
        "sofrRateBps": pricing.sofr_bps,
        "sofrAsOf": pricing.sofr_as_of,
        "sofrSource": pricing.sofr_source,
        "buyerRiskScore": pricing.buyer_risk_score,
        "riskSpreadBps": pricing.buyer_risk_spread_bps,
        "countryLegalSpreadBps": pricing.country_legal_spread_bps,
        "annualExpectedYieldBps": pricing.investor_net_annual_yield_bps,
        "platformFeeShareBps": pricing.platform_fee_share_bps,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(fixture(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != rendered:
            raise SystemExit("demo pricing fixture is stale; regenerate it")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
