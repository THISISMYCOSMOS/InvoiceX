"""Replaceable risk-scoring boundary.

The provider owns score calculation only.  It never approves a transaction;
the mandate and idempotency checks in ``InvoiceService`` remain authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from invoicex_backend.models import RiskEligibility
from invoicex_backend.policy import DeterministicRiskPolicy


@dataclass(frozen=True, slots=True)
class RiskScoringRequest:
    invoice_id: str
    face_value_usdc: int
    has_document_mismatches: bool
    buyer_confirmed: bool
    remaining_term_days: int
    document_summary: str


@dataclass(frozen=True, slots=True)
class RiskScoringResult:
    score: int
    eligibility: RiskEligibility
    advance_rate_bps: int | None
    advance_amount_usdc: int | None
    factors: tuple[str, ...]
    provider: str
    method_version: str


class RiskScoringProvider(Protocol):
    def evaluate(self, request: RiskScoringRequest) -> RiskScoringResult: ...


class DeterministicRiskScoringProvider:
    """Compatibility adapter for the existing 68/86 policy."""

    provider_name = "deterministic"

    def __init__(self, policy: DeterministicRiskPolicy | None = None) -> None:
        self._policy = policy or DeterministicRiskPolicy()

    def evaluate(self, request: RiskScoringRequest) -> RiskScoringResult:
        decision = self._policy.evaluate(
            has_mismatches=request.has_document_mismatches,
            face_value_usdc=request.face_value_usdc,
        )
        factors = (
            "DOCUMENT_MISMATCH" if request.has_document_mismatches else "DOCUMENT_CONSISTENCY",
            "BUYER_CONFIRMED" if request.buyer_confirmed else "BUYER_PENDING",
        )
        return RiskScoringResult(
            score=decision.score,
            eligibility=decision.eligibility,
            advance_rate_bps=decision.advance_rate_bps,
            advance_amount_usdc=decision.advance_amount_usdc,
            factors=factors,
            provider=self.provider_name,
            method_version=self._policy.policy_version,
        )
