from __future__ import annotations

from invoicex_backend.models import InvestorMandate, MandatePolicy
from invoicex_backend.repository import SQLiteRwaRepository


def test_new_mandate_replaces_the_previous_active_mandate_for_one_wallet(tmp_path) -> None:
    repository = SQLiteRwaRepository(tmp_path / "rwa.sqlite3")
    policy = MandatePolicy(
        total_investment_limit_usdc=5,
        per_invoice_limit_usdc=1,
        buyer_allowlist=["Prime Mobility"],
        minimum_risk_score=80,
        maximum_remaining_term_days=120,
        expires_at="2030-12-31",
    )
    first = InvestorMandate(
        id="MAN-first",
        owner_wallet_address="wallet-address",
        vault_address="vault-address",
        policy=policy,
        canonical_message="first",
        signature="signature",
        created_at="2026-08-02T00:00:00Z",
    )
    second = first.model_copy(
        update={
            "id": "MAN-second",
            "canonical_message": "second",
            "created_at": "2026-08-02T00:01:00Z",
        }
    )

    repository.save_mandate(first)
    repository.save_mandate(second)

    assert [mandate.id for mandate in repository.active_mandates()] == ["MAN-second"]
    repository.close()
