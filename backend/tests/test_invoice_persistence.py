"""Regression test for invoice/analysis/verification persistence across restarts.

Before this change, InvoiceService kept `_invoices`, `_agent_analyses`, and
`_verifications` only in memory (service.py `__init__`), while
`SQLiteRwaRepository` durably stored only mandate/vault/RWA-asset/
agent-decision rows. A process restart therefore dropped every invoice
while leaving its RWA/decision rows orphaned, and the id sequence counters
reset to zero, which would collide with previously issued invoice ids.

Each stage below drives the invoice through one state transition, then
builds a brand-new `InvoiceService`/app bound to the same sqlite database
and upload directory (simulating a backend restart) and asserts the state
is still there before continuing.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from solders.keypair import Keypair

from invoicex_backend.app import create_app
from invoicex_backend.config import BackendSettings

from tests.conftest import mock_settings


def _restart_client(settings: BackendSettings) -> TestClient:
    """A fresh app/service pointed at the same sqlite/upload paths as
    `settings`, i.e. what the next process would build after a restart."""

    return TestClient(create_app(settings=settings))


def _create_signed_mandate(client: TestClient, *, policy: dict[str, object]) -> Keypair:
    investor = Keypair()
    prepared = client.post(
        "/api/v1/investor/mandates/prepare",
        json={"ownerWalletAddress": str(investor.pubkey()), "policy": policy},
    )
    assert prepared.status_code == 200
    signature = str(investor.sign_message(prepared.json()["canonicalMessage"].encode()))
    created = client.post(
        "/api/v1/investor/mandates",
        json={
            "ownerWalletAddress": str(investor.pubkey()),
            "policy": policy,
            "signature": signature,
        },
    )
    assert created.status_code == 200
    return investor


def test_invoice_state_survives_a_backend_restart_at_every_stage(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    settings = mock_settings(tmp_path / "uploads")

    with _restart_client(settings) as client:
        created = client.post("/api/v1/invoices", files=contract_files)
        assert created.status_code == 201
        invoice = created.json()["invoice"]
        invoice_id = invoice["id"]
        analysis_before = invoice["analysis"]
        assert analysis_before is not None

    # 1. Invoice creation + Document Agent analysis survive a restart.
    with _restart_client(settings) as client:
        listed = client.get("/api/v1/invoices").json()["items"]
        assert any(item["id"] == invoice_id for item in listed)
        fetched = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert fetched["status"] == "DOCUMENT_REVIEW_REQUIRED"
        assert fetched["analysis"] == analysis_before

        verification_response = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        )
        assert verification_response.status_code == 200
        verification_id = verification_response.json()["invoice"]["verificationId"]
        assert verification_id is not None

    # 2. The Buyer verification request survives a restart.
    with _restart_client(settings) as client:
        fetched = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert fetched["status"] == "BUYER_REVIEW"
        assert fetched["verificationId"] == verification_id
        verifications = client.get("/api/v1/verifications").json()["items"]
        assert any(item["id"] == verification_id for item in verifications)

        confirmed = client.post(f"/api/v1/verifications/{verification_id}/confirm")
        assert confirmed.status_code == 200
        risk_passport_before = confirmed.json()["invoice"]["riskPassport"]
        assert risk_passport_before is not None

    # 3. Buyer Confirm and the generated Risk Passport survive a restart.
    with _restart_client(settings) as client:
        fetched = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert fetched["status"] == "OFFER_READY"
        assert fetched["riskPassport"] == risk_passport_before

        policy = {
            "totalInvestmentLimitUsdc": 20_000,
            "perInvoiceLimitUsdc": 20_000,
            "buyerAllowlist": ["Prime Mobility"],
            "minimumRiskScore": 0,
            "maximumRemainingTermDays": 365,
            "expiresAt": "2030-12-31",
        }
        investor = _create_signed_mandate(client, policy=policy)
        deposited = client.post(
            "/api/v1/investor/vault/deposits/confirm",
            json={
                "ownerWalletAddress": str(investor.pubkey()),
                "amountUsdc": 20_000,
                "signature": "mock-deposit-signature-persistence-test",
            },
        )
        assert deposited.status_code == 200

        offer_response = client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )
        assert offer_response.status_code == 200
        # respond_to_offer returns RWA_ISSUED; the automatic mandate match and
        # buy run as a background task scheduled by the same request, so the
        # final FUNDED status is only visible on a follow-up read.
        after_funding = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert after_funding["status"] == "FUNDED"

    # 4. RWA issuance, mandate matching, and the automatic buy (FUNDED) survive
    # a restart, including the agentDecision and fundingTransaction records
    # that live in the separate rwa/decision tables.
    with _restart_client(settings) as client:
        fetched = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert fetched["status"] == "FUNDED"
        assert fetched["agentDecision"] is not None
        assert fetched["agentDecision"]["status"] == "EXECUTED"
        assert fetched["fundingTransaction"] is not None

        # 5. Id-collision guard: without sequence restoration the fresh
        # service's counter would restart at 0 and reissue `invoice_id`.
        second = client.post("/api/v1/invoices", files=contract_files)
        assert second.status_code == 201
        second_invoice_id = second.json()["invoice"]["id"]
        assert second_invoice_id != invoice_id
