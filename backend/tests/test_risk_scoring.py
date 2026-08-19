from invoicex_backend.models import RiskEligibility
from invoicex_backend.risk_scoring import DeterministicRiskScoringProvider, RiskScoringRequest


def _request(*, mismatch: bool) -> RiskScoringRequest:
    return RiskScoringRequest(
        invoice_id="INV-1",
        face_value_usdc=100,
        has_document_mismatches=mismatch,
        buyer_confirmed=True,
        remaining_term_days=90,
        document_summary="test",
    )


def test_deterministic_provider_preserves_existing_68_86_policy() -> None:
    provider = DeterministicRiskScoringProvider()
    eligible = provider.evaluate(_request(mismatch=False))
    review = provider.evaluate(_request(mismatch=True))

    assert (eligible.score, eligible.eligibility, eligible.advance_amount_usdc) == (
        86,
        RiskEligibility.ELIGIBLE,
        94,
    )
    assert (review.score, review.eligibility, review.advance_amount_usdc) == (
        68,
        RiskEligibility.REVIEW_REQUIRED,
        None,
    )
    assert sum(factor.score or 0 for factor in eligible.factors) == eligible.score
    assert sum(factor.score or 0 for factor in review.factors) == review.score
    assert eligible.data_coverage_bps == 10_000
    assert {factor.source for factor in eligible.factors} == {
        "SYNTHETIC_DEMO_DATA",
        "INVOICE_DATA",
        "INVOICEX_DATA",
        "DOCUMENT_AGENT",
    }
