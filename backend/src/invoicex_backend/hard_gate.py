"""Deterministic eligibility gates evaluated before any Risk Score is produced."""

from __future__ import annotations

from dataclasses import dataclass

from invoicex_backend.models import HardGateCheck, HardGateResult


@dataclass(frozen=True, slots=True)
class HardGateInput:
    buyer_confirmed: bool
    supplier_verified: bool
    buyer_verified: bool
    delivery_completed: bool
    dispute_free: bool
    duplicate_free: bool
    not_overdue: bool
    prior_assignment_free: bool
    sanctions_clear: bool


_CHECKS = (
    ("BUYER_CONFIRMED", "구매기업 확인 완료", "구매기업 확인이 완료되지 않았습니다."),
    ("SUPPLIER_VERIFIED", "공급기업 인증 완료", "공급기업 인증이 완료되지 않았습니다."),
    ("BUYER_VERIFIED", "구매기업 인증 완료", "구매기업 인증이 완료되지 않았습니다."),
    ("DELIVERY_COMPLETED", "납품 완료", "납품 완료 근거가 확인되지 않았습니다."),
    ("NO_DISPUTE", "분쟁 없음", "분쟁 상태인 인보이스입니다."),
    ("NO_DUPLICATE", "중복 인보이스 없음", "동일한 원본 인보이스가 이미 등록되어 있습니다."),
    ("NOT_OVERDUE", "만기 전", "이미 만기가 지난 인보이스입니다."),
    ("NO_PRIOR_ASSIGNMENT", "선행 양도 없음", "기존 채권 양도 이력이 확인되었습니다."),
    ("SANCTIONS_CLEAR", "제재 대상 아님", "제재 목록 확인을 통과하지 못했습니다."),
)


def evaluate_hard_gate(value: HardGateInput) -> HardGateResult:
    flags = (
        value.buyer_confirmed,
        value.supplier_verified,
        value.buyer_verified,
        value.delivery_completed,
        value.dispute_free,
        value.duplicate_free,
        value.not_overdue,
        value.prior_assignment_free,
        value.sanctions_clear,
    )
    checks = [
        HardGateCheck(key=key, label=label, passed=passed, reason=None if passed else reason)
        for (key, label, reason), passed in zip(_CHECKS, flags, strict=True)
    ]
    failures = [check.reason for check in checks if not check.passed and check.reason]
    return HardGateResult(passed=not failures, checks=checks, failure_reasons=failures)
