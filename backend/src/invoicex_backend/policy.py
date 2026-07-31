"""Deterministic Risk and AP2 mandate decisions."""

from __future__ import annotations

from dataclasses import dataclass

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import Invoice, RiskEligibility


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

    def evaluate(
        self,
        *,
        has_mismatches: bool,
        face_value_usdc: int,
        buyer_dispute: bool = False,
        buyer_mismatches: bool = False,
    ) -> RiskDecision:
        if buyer_dispute:
            # A buyer-declared dispute or payment hold is not investable.
            return RiskDecision(
                score=0,
                level="BLOCKED",
                eligibility=RiskEligibility.BLOCKED,
                advance_rate_bps=None,
                advance_amount_usdc=None,
            )
        if has_mismatches or buyer_mismatches:
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


class TreasuryMandatePolicy:
    """AP2-style deterministic guard checked immediately before wallet execution."""

    def __init__(self, settings: BackendSettings) -> None:
        self._minimum_score = settings.mandate_min_risk_score
        self._maximum_advance = settings.mandate_max_advance_usdc

    def rejection_reason(self, invoice: Invoice) -> str | None:
        passport = invoice.risk_passport
        if passport is None:
            return "Risk Passport가 없습니다."
        if passport.eligibility is not RiskEligibility.ELIGIBLE:
            return "Risk Passport가 투자 적격 상태가 아닙니다."
        if passport.risk_score is None or passport.risk_score < self._minimum_score:
            return "Risk Score가 Mandate 최소 기준보다 낮습니다."
        if (
            passport.suggested_advance_amount_usdc is None
            or passport.suggested_advance_amount_usdc > self._maximum_advance
        ):
            return "조기정산금이 Mandate 건별 한도를 초과합니다."
        return None
