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
class RiskScoreFactorResult:
    key: str
    label: str
    score: int | None
    max_score: int
    source: str
    detail: str
    synthetic: bool = False


@dataclass(frozen=True, slots=True)
class RiskScoringResult:
    score: int
    eligibility: RiskEligibility
    advance_rate_bps: int | None
    advance_amount_usdc: int | None
    factors: tuple[RiskScoreFactorResult, ...]
    data_coverage_bps: int
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
            RiskScoreFactorResult(
                key="BUYER_CREDIT_QUALITY",
                label="Buyer Credit Quality",
                score=22,
                max_score=25,
                source="SYNTHETIC_DEMO_DATA",
                detail="A-equivalent synthetic corporate credit profile",
                synthetic=True,
            ),
            RiskScoreFactorResult(
                key="BUYER_PAYMENT_HISTORY",
                label="Buyer Payment History",
                score=18,
                max_score=20,
                source="SYNTHETIC_DEMO_DATA",
                detail="1 late payment across 24 synthetic invoices",
                synthetic=True,
            ),
            RiskScoreFactorResult(
                key="SUPPLIER_BUYER_HISTORY",
                label="Supplier–Buyer Transaction History",
                score=13,
                max_score=15,
                source="SYNTHETIC_DEMO_DATA",
                detail="24 synthetic prior transactions",
                synthetic=True,
            ),
            RiskScoreFactorResult(
                key="REMAINING_MATURITY",
                label="Remaining Maturity",
                score=8,
                max_score=10,
                source="INVOICE_DATA",
                detail=f"{request.remaining_term_days} days remaining",
            ),
            RiskScoreFactorResult(
                key="INVOICE_CONCENTRATION",
                label="Invoice Size / Concentration",
                score=5,
                max_score=5,
                source="INVOICEX_DATA",
                detail=f"{request.face_value_usdc:,} USDC invoice exposure",
            ),
            RiskScoreFactorResult(
                key="DOCUMENT_INTEGRITY",
                label="Document Integrity & Anomaly",
                score=2 if request.has_document_mismatches else 20,
                max_score=25,
                source="DOCUMENT_AGENT",
                detail=request.document_summary,
            ),
        )
        return RiskScoringResult(
            score=decision.score,
            eligibility=decision.eligibility,
            advance_rate_bps=decision.advance_rate_bps,
            advance_amount_usdc=decision.advance_amount_usdc,
            factors=factors,
            data_coverage_bps=10_000,
            provider=self.provider_name,
            method_version=self._policy.policy_version,
        )
