"""Transparent MVP breakdown for the existing early-settlement advance.

The current policy already fixes the supplier advance at 94% for eligible
invoices.  This module does not introduce a new pricing engine; it only splits
the existing haircut into an explicit discount and a temporary reserve so the
supplier can understand the economics before RWA issuance.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EarlySettlementBreakdown:
    face_value_usdc: int
    discount_amount_usdc: int
    discount_rate_bps: int
    investor_required_return_usdc: int
    platform_fee_usdc: int
    reserve_amount_usdc: int
    reserve_rate_bps: int
    initial_advance_usdc: int
    expected_reserve_return_usdc: int
    expected_final_proceeds_usdc: int


def calculate_early_settlement_breakdown(
    *,
    face_value_usdc: int,
    advance_amount_usdc: int,
) -> EarlySettlementBreakdown:
    """Split the existing policy haircut into discount (2/3) and reserve (1/3)."""

    if face_value_usdc < 0 or advance_amount_usdc < 0:
        raise ValueError("Early-settlement values cannot be negative")
    if advance_amount_usdc > face_value_usdc:
        raise ValueError("Advance amount cannot exceed invoice face value")

    total_haircut = face_value_usdc - advance_amount_usdc
    reserve_amount = total_haircut // 3
    discount_amount = total_haircut - reserve_amount
    investor_required_return = discount_amount * 7 // 10
    platform_fee = discount_amount - investor_required_return

    def rate_bps(amount: int) -> int:
        return amount * 10_000 // face_value_usdc if face_value_usdc else 0

    return EarlySettlementBreakdown(
        face_value_usdc=face_value_usdc,
        discount_amount_usdc=discount_amount,
        discount_rate_bps=rate_bps(discount_amount),
        investor_required_return_usdc=investor_required_return,
        platform_fee_usdc=platform_fee,
        reserve_amount_usdc=reserve_amount,
        reserve_rate_bps=rate_bps(reserve_amount),
        initial_advance_usdc=advance_amount_usdc,
        expected_reserve_return_usdc=reserve_amount,
        expected_final_proceeds_usdc=advance_amount_usdc + reserve_amount,
    )
