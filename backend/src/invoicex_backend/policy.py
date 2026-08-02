"""Deterministic Risk and AP2 mandate decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import (
    InvestorMandate,
    Invoice,
    MandateStatus,
    RiskEligibility,
)


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


class TreasuryMandatePolicy:
    """AP2-style deterministic guard checked immediately before wallet execution."""

    def __init__(self, settings: BackendSettings) -> None:
        self._minimum_score = settings.mandate_min_risk_score
        self._maximum_advance = settings.mandate_max_advance_usdc

    def rejection_reason(
        self,
        invoice: Invoice,
        *,
        mandate: InvestorMandate | None = None,
        outstanding_principal_usdc: int = 0,
        daily_invested_usdc: int = 0,
        available_vault_usdc: int | None = None,
        today: date | None = None,
    ) -> str | None:
        passport = invoice.risk_passport
        if passport is None:
            return "Risk Passport가 없습니다."
        if passport.eligibility is not RiskEligibility.ELIGIBLE:
            return "Risk Passport가 투자 적격 상태가 아닙니다."

        if mandate is None:
            # No Mandate on file: fall back to the fixed settings-based guard
            # unchanged, so callers that never pass a Mandate keep today's
            # behavior exactly.
            if passport.risk_score is None or passport.risk_score < self._minimum_score:
                return "Risk Score가 Mandate 최소 기준보다 낮습니다."
            if (
                passport.suggested_advance_amount_usdc is None
                or passport.suggested_advance_amount_usdc > self._maximum_advance
            ):
                return "조기정산금이 Mandate 건별 한도를 초과합니다."
            return None

        if mandate.emergency_stopped:
            return "투자자가 긴급 중지를 설정했습니다."
        if mandate.status is not MandateStatus.ACTIVE:
            return "Mandate가 활성 상태가 아닙니다."

        resolved_today = today if today is not None else datetime.now(UTC).date()
        try:
            valid_from = date.fromisoformat(mandate.valid_from)
            valid_until = date.fromisoformat(mandate.valid_until)
        except ValueError:
            return "Mandate 유효기간이 아닙니다."
        if not (valid_from <= resolved_today <= valid_until):
            return "Mandate 유효기간이 아닙니다."

        if passport.risk_score is None or passport.risk_score < mandate.min_risk_score:
            return "Risk Score가 Mandate 최소 기준보다 낮습니다."

        if invoice.buyer.id in mandate.excluded_buyer_ids:
            return "제외된 구매기업입니다."
        if mandate.buyer_allowlist and invoice.buyer.id not in mandate.buyer_allowlist:
            return "허용된 구매기업 목록에 없습니다."

        advance_rate_bps = passport.suggested_advance_rate_bps
        if advance_rate_bps is None or advance_rate_bps > mandate.max_advance_rate_bps:
            return "선지급률이 Mandate 한도를 초과합니다."

        try:
            due_date = date.fromisoformat(invoice.due_date)
        except ValueError:
            return "만기일 형식을 확인할 수 없습니다."
        remaining_tenor_days = (due_date - resolved_today).days
        if (
            remaining_tenor_days < 0
            or remaining_tenor_days > mandate.max_remaining_tenor_days
        ):
            return "잔존 만기가 Mandate 허용 범위를 벗어납니다."

        advance_amount = passport.suggested_advance_amount_usdc
        if advance_amount is None or advance_amount > mandate.per_invoice_limit_usdc:
            return "조기정산금이 Mandate 건별 한도를 초과합니다."
        if (
            outstanding_principal_usdc + advance_amount
            > mandate.total_outstanding_limit_usdc
        ):
            return "총 미상환 투자잔액 한도를 초과합니다."
        if (
            daily_invested_usdc + advance_amount
            > mandate.daily_new_investment_limit_usdc
        ):
            return "일일 신규 투자 한도를 초과합니다."
        if available_vault_usdc is not None and advance_amount > available_vault_usdc:
            return "Agent Vault 잔액이 부족합니다."
        return None
