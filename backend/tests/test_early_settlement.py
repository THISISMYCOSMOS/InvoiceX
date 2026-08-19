import pytest

from invoicex_backend.early_settlement import calculate_early_settlement_breakdown


def test_existing_94_percent_advance_is_split_into_discount_and_reserve() -> None:
    terms = calculate_early_settlement_breakdown(
        face_value_usdc=96_000,
        advance_amount_usdc=90_240,
    )

    assert terms.discount_amount_usdc == 3_840
    assert terms.reserve_amount_usdc == 1_920
    assert terms.initial_advance_usdc == 90_240
    assert terms.expected_final_proceeds_usdc == 92_160
    assert terms.investor_required_return_usdc + terms.platform_fee_usdc == terms.discount_amount_usdc
    assert terms.discount_amount_usdc + terms.reserve_amount_usdc == 5_760


def test_advance_cannot_exceed_face_value() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        calculate_early_settlement_breakdown(face_value_usdc=100, advance_amount_usdc=101)
