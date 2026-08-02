"""Deterministic Risk decisions.

Mandate gating lives in InvoiceService._evaluate_mandate, which checks the
investor's wallet-signed policy rather than static settings.
"""

from __future__ import annotations

from dataclasses import dataclass

from invoicex_backend.models import RiskEligibility


@dataclass(frozen=True, slots=True)
class RiskDecision:
    score: int
    level: str
    eligibility: RiskEligibility
    advance_rate_bps: int | None
    advance_amount_usdc: int | None


class DeterministicRiskPolicy:
    """Calculate financial decisions without allowing an LLM to modify them."""

    policy_version = "v1"

    def evaluate(self, *, has_mismatches: bool, face_value_usdc: int) -> RiskDecision:
        if has_mismatches:
            return RiskDecision(
                score=68,
                level="REVIEW_REQUIRED",
                eligibility=RiskEligibility.REVIEW_REQUIRED,
                advance_rate_bps=None,
                advance_amount_usdc=None,
            )
        advance_rate_bps = 9_400
        return RiskDecision(
            score=86,
            level="POLICY_ACCEPTABLE",
            eligibility=RiskEligibility.ELIGIBLE,
            advance_rate_bps=advance_rate_bps,
            advance_amount_usdc=face_value_usdc * advance_rate_bps // 10_000,
        )
