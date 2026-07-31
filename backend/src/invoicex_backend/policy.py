"""Deterministic Risk and AP2 mandate decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import InvestorMandate, Invoice, RiskEligibility


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


def default_mandate(settings: BackendSettings) -> InvestorMandate:
    """Fall back to the environment policy until an investor saves their own."""

    return InvestorMandate(
        deposit_usdc=50_000,
        total_limit_usdc=50_000,
        per_invoice_limit_usdc=settings.mandate_max_advance_usdc,
        buyer_allowlist=["BUYER_PRIME"],
        minimum_risk_score=settings.mandate_min_risk_score,
        maximum_term_days=120,
        policy_expires_on=f"{date.today().year}-12-31",
    )


class TreasuryMandatePolicy:
    """AP2-style deterministic guard checked immediately before wallet execution.

    Every field InvestorSetupPage collects is enforced here, so saving the form
    actually changes what the Treasury Agent will buy.
    """

    def rejection_reason(
        self,
        invoice: Invoice,
        mandate: InvestorMandate,
        outstanding_usdc: int = 0,
        today: date | None = None,
    ) -> str | None:
        passport = invoice.risk_passport
        if passport is None:
            return "Risk Passport가 없습니다."
        if passport.eligibility is not RiskEligibility.ELIGIBLE:
            return "Risk Passport가 투자 적격 상태가 아닙니다."
        if mandate.status != "ACTIVE":
            return "AP2 Mandate가 활성 상태가 아닙니다."

        now = today or date.today()
        expiry = _parse_date(mandate.policy_expires_on)
        if expiry is None:
            return "Mandate 정책 만료일을 해석할 수 없습니다."
        if expiry < now:
            return "AP2 Mandate 정책이 만료되었습니다."

        if passport.risk_score is None or passport.risk_score < mandate.minimum_risk_score:
            return "Risk Score가 Mandate 최소 기준보다 낮습니다."

        advance = passport.suggested_advance_amount_usdc
        if advance is None or advance > mandate.per_invoice_limit_usdc:
            return "조기정산금이 Mandate 건별 한도를 초과합니다."
        if outstanding_usdc + advance > mandate.total_limit_usdc:
            return "Mandate 총 투자 한도를 초과합니다."
        if advance > mandate.deposit_usdc - outstanding_usdc:
            return "Vault 예치 잔액이 부족합니다."

        if invoice.buyer.id not in mandate.buyer_allowlist:
            return "구매기업이 Mandate 허용 목록에 없습니다."

        due = _parse_date(invoice.due_date)
        if due is None:
            return "인보이스 만기일을 해석할 수 없습니다."
        if (due - now).days > mandate.maximum_term_days:
            return "잔존 만기가 Mandate 최대 기준을 초과합니다."
        return None


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
