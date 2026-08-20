"""Risk decision DTO shared by scoring and canonical pricing orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from invoicex_backend.models import RiskEligibility


@dataclass(frozen=True, slots=True)
class RiskDecision:
    score: int
    level: str
    eligibility: RiskEligibility
    advance_rate_bps: int | None
    advance_amount_usdc: Decimal | None
