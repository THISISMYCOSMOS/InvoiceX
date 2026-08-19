"""Regression test for buyer-allowlist matching against extracted documents.

An uploaded buyer name must not be silently replaced with the old Demo buyer
identity. A genuinely different buyer therefore requires a matching mandate
allowlist entry instead of inheriting Prime Mobility's approval.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from invoicex_agents.models.document import DocumentAnalysisResult
from solders.keypair import Keypair

from invoicex_backend.agents import AgentDocument, MockAgentGateway
from invoicex_backend.app import create_app
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import create_solana_gateway
from invoicex_backend.storage import LocalDocumentStorage
from tests.conftest import mock_settings


class KoreanBuyerNameAgentGateway(MockAgentGateway):
    """Deterministic mock gateway that extracts a Korean buyer company name,
    mirroring what the real Gemini Document Agent returns for a
    Korean-registered buyer, without touching MockAgentGateway's own default
    ("Prime Mobility") used by other tests."""

    async def analyze_documents(
        self,
        invoice_id: str,
        documents: list[AgentDocument],
    ) -> DocumentAnalysisResult:
        response = self._document_response(invoice_id, documents)
        for document in response["documents"]:
            if document["extractedData"].get("buyerName") == "Prime Mobility":
                document["extractedData"]["buyerName"] = "(주)프라임모빌리티"
            for evidence in document["sourceEvidence"]:
                if evidence["field"] == "buyerName":
                    evidence["quote"] = "(주)프라임모빌리티"
        return DocumentAnalysisResult.model_validate(response)


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


def test_mandate_rejects_unlisted_extracted_buyer_name(
    tmp_path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    settings = mock_settings(tmp_path / "uploads")
    storage = LocalDocumentStorage(settings)
    service = InvoiceService(
        settings=settings,
        agent_gateway=KoreanBuyerNameAgentGateway(),
        solana_gateway=create_solana_gateway(settings),
        storage=storage,
    )
    app = create_app(settings=settings, service=service)
    with TestClient(app) as client:
        policy = {
            "totalInvestmentLimitUsdc": 20_000,
            "perInvoiceLimitUsdc": 20_000,
            "buyerAllowlist": ["Prime Mobility"],
            "minimumRiskScore": 80,
            "maximumRemainingTermDays": 100,
            "expiresAt": "2030-12-31",
        }
        investor = _create_signed_mandate(client, policy=policy)
        deposited = client.post(
            "/api/v1/investor/vault/deposits/confirm",
            json={
                "ownerWalletAddress": str(investor.pubkey()),
                "amountUsdc": 20_000,
                "signature": "mock-deposit-signature-korean-buyer",
            },
        )
        assert deposited.status_code == 200

        created = client.post("/api/v1/invoices", files=contract_files)
        assert created.status_code == 201
        invoice_id = created.json()["invoice"]["id"]
        assert (
            created.json()["invoice"]["analysis"]["buyerName"]["value"]
            == "(주)프라임모빌리티"
        )

        verification = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        confirmed = client.post(f"/api/v1/verifications/{verification}/confirm")
        assert confirmed.status_code == 200

        response = client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )
        assert response.status_code == 200

        final = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert final["buyer"]["name"] == "(주)프라임모빌리티"
        assert final["agentDecision"]["checks"]["buyerAllowlist"] is False
        assert final["status"] == "RWA_ISSUED"
