from invoicex_backend.models import RiskEligibility
from invoicex_backend.risk_scoring import DeterministicRiskScoringProvider, RiskScoringRequest


def _request(*, mismatch: bool, invoice_id: str = "INV-1") -> RiskScoringRequest:
    return RiskScoringRequest(
        invoice_id=invoice_id,
        face_value_base_units=100_000_000,
        has_document_mismatches=mismatch,
        buyer_confirmed=True,
        remaining_term_days=90,
        document_summary="test",
        buyer_key="BUYER-1",
        supplier_key="SUPPLIER-1",
    )


def test_rule_engine_is_deterministic_and_respects_component_weights() -> None:
    provider = DeterministicRiskScoringProvider()
    first = provider.evaluate(_request(mismatch=False))
    second = provider.evaluate(_request(mismatch=False))

    assert first == second
    assert first.eligibility in {RiskEligibility.ELIGIBLE, RiskEligibility.REVIEW_REQUIRED}
    assert sum(factor.score or 0 for factor in first.factors) == first.score
    assert {factor.key: factor.max_score for factor in first.factors} == {
        "BUYER_CREDIT_QUALITY": 45,
        "BUYER_PAYMENT_HISTORY": 30,
        "SUPPLIER_BUYER_HISTORY": 15,
        "REMAINING_MATURITY": 10,
    }
    assert all((factor.score or 0) <= factor.max_score for factor in first.factors)
    assert first.data_coverage_bps == 10_000
    assert {factor.source for factor in first.factors} == {
        "SYNTHETIC_DEMO_DATA",
        "INVOICE_DATA",
    }


def test_rule_engine_uses_stable_identity_inputs_without_randomness() -> None:
    provider = DeterministicRiskScoringProvider()
    first = provider.evaluate(_request(mismatch=False, invoice_id="INV-1"))
    other = provider.evaluate(_request(mismatch=False, invoice_id="INV-2"))

    assert provider.evaluate(_request(mismatch=False, invoice_id="INV-2")) == other
    assert first.method_version == "risk-rules-v2"
