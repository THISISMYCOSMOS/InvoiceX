"""Replaceable risk-scoring boundary.

The provider owns score calculation only.  It never approves a transaction;
the mandate and idempotency checks in ``InvoiceService`` remain authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from invoicex_backend.models import RiskEligibility
import hashlib


@dataclass(frozen=True, slots=True)
class RiskScoringRequest:
    invoice_id: str
    face_value_usdc: int
    has_document_mismatches: bool
    buyer_confirmed: bool
    remaining_term_days: int
    document_summary: str
    buyer_key: str = ""
    supplier_key: str = ""


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
    """Rule-based score with stable, explainable inputs and no randomness."""

    provider_name = "deterministic"

    method_version = "risk-rules-v2"

    @staticmethod
    def _stable_ratio(key: str, lower: int, upper: int) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return lower + int.from_bytes(digest[:4], "big") % (upper - lower + 1)

    def evaluate(self, request: RiskScoringRequest) -> RiskScoringResult:
        buyer_key = request.buyer_key or request.invoice_id
        relationship_key = f"{request.supplier_key}:{buyer_key}"
        credit_score = self._stable_ratio(f"credit:{buyer_key}", 34, 43)
        payment_score = self._stable_ratio(f"payment:{buyer_key}", 22, 29)
        relationship_score = self._stable_ratio(f"relationship:{relationship_key}", 10, 15)
        days = max(0, request.remaining_term_days)
        maturity_score = 10 if days <= 30 else 9 if days <= 60 else 8 if days <= 90 else 6 if days <= 180 else 3
        total = credit_score + payment_score + relationship_score + maturity_score
        eligibility = RiskEligibility.ELIGIBLE if total >= 70 else RiskEligibility.BLOCKED
        factors = (
            RiskScoreFactorResult(
                key="BUYER_CREDIT_QUALITY",
                label="Buyer Credit Quality",
                score=credit_score,
                max_score=45,
                source="SYNTHETIC_DEMO_DATA",
                detail="등록 기업 식별자를 기준으로 산출한 deterministic 구매기업 신용 규칙 점수",
                synthetic=True,
            ),
            RiskScoreFactorResult(
                key="BUYER_PAYMENT_HISTORY",
                label="Buyer Payment History",
                score=payment_score,
                max_score=30,
                source="SYNTHETIC_DEMO_DATA",
                detail="구매기업 식별자를 기준으로 산출한 deterministic 지급 이력 규칙 점수",
                synthetic=True,
            ),
            RiskScoreFactorResult(
                key="SUPPLIER_BUYER_HISTORY",
                label="Supplier–Buyer Transaction History",
                score=relationship_score,
                max_score=15,
                source="SYNTHETIC_DEMO_DATA",
                detail="공급기업과 구매기업 식별자를 기준으로 산출한 deterministic 거래 관계 규칙 점수",
                synthetic=True,
            ),
            RiskScoreFactorResult(
                key="REMAINING_MATURITY",
                label="Remaining Maturity",
                score=maturity_score,
                max_score=10,
                source="INVOICE_DATA",
                detail=f"{request.remaining_term_days} days remaining",
            ),
        )
        return RiskScoringResult(
            score=total,
            eligibility=eligibility,
            advance_rate_bps=None,
            advance_amount_usdc=None,
            factors=factors,
            data_coverage_bps=10_000,
            provider=self.provider_name,
            method_version=self.method_version,
        )
