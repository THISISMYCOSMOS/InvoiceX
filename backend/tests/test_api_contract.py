from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient
from solders.keypair import Keypair

from invoicex_backend.agent_activity import AgentTrigger
from invoicex_backend.app import create_app
from tests.conftest import mock_settings


class RecordingTaskDispatcher:
    def __init__(self) -> None:
        self.tasks: list[tuple[str, AgentTrigger]] = []

    async def enqueue(self, invoice_id: str, trigger: AgentTrigger) -> None:
        self.tasks.append((invoice_id, trigger))


def test_invoice_creation_queues_analysis_without_waiting_for_agent(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    dispatcher = RecordingTaskDispatcher()
    app = create_app(
        settings=mock_settings(tmp_path / "uploads"),
        agent_task_dispatcher=dispatcher,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/invoices", files=contract_files)

    assert response.status_code == 201
    invoice = response.json()["invoice"]
    assert invoice["status"] == "DOCUMENT_ANALYZING"
    assert dispatcher.tasks == [(invoice["id"], AgentTrigger.INVOICE_CREATED)]


def test_risk_review_request_persists_review_requested_status(
    client: TestClient,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    created = client.post("/api/v1/invoices", files=contract_files).json()["invoice"]
    invoice_id = created["id"]

    verification = client.post(f"/api/v1/invoices/{invoice_id}/verification-request").json()["invoice"]
    verification_id = verification["verificationId"]
    offered = client.post(f"/api/v1/verifications/{verification_id}/confirm").json()["invoice"]
    assert offered["status"] == "OFFER_READY"

    requested = client.post(f"/api/v1/invoices/{invoice_id}/risk-review-request")
    assert requested.status_code == 200
    assert requested.json()["invoice"]["status"] == "REVIEW_REQUESTED"
    assert requested.json()["invoice"]["agentTraces"][-1]["status"] == "SUBMITTED"

    duplicate = client.post(f"/api/v1/invoices/{invoice_id}/risk-review-request")
    assert duplicate.status_code == 200
    assert duplicate.json()["invoice"]["status"] == "REVIEW_REQUESTED"
    persisted = client.get(f"/api/v1/invoices/{invoice_id}")
    assert persisted.status_code == 200
    assert persisted.json()["invoice"]["status"] == "REVIEW_REQUESTED"


def test_same_original_invoice_number_does_not_block_a_new_invoice(
    client: TestClient,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    first = client.post("/api/v1/invoices", files=contract_files).json()["invoice"]
    second = client.post("/api/v1/invoices", files=contract_files).json()["invoice"]

    service = client.app.state.invoice_service
    second_invoice = service._invoices[second["id"]]
    second_invoice.analysis.invoice_number.value = first["analysis"]["invoiceNumber"]["value"]
    service._save_invoice(second_invoice)

    for invoice in (first, second):
        requested = client.post(
            f"/api/v1/invoices/{invoice['id']}/verification-request"
        ).json()["invoice"]
        confirmed = client.post(
            f"/api/v1/verifications/{requested['verificationId']}/confirm"
        ).json()["invoice"]

        assert confirmed["status"] == "OFFER_READY"
        assert confirmed["riskPassport"]["hardGate"]["passed"] is True
        assert "NO_DUPLICATE" not in {
            check["key"] for check in confirmed["riskPassport"]["hardGate"]["checks"]
        }


def test_buyer_reject_persists_reason_and_supplier_can_request_review(
    client: TestClient,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    created = client.post("/api/v1/invoices", files=contract_files).json()["invoice"]
    invoice_id = created["id"]
    requested = client.post(f"/api/v1/invoices/{invoice_id}/verification-request").json()["invoice"]

    rejected = client.post(
        f"/api/v1/verifications/{requested['verificationId']}/reject",
        json={
            "reasonCode": "DOCUMENT_MISMATCH",
            "detail": "PO 금액과 인보이스 금액을 다시 확인해 주세요.",
        },
    )

    assert rejected.status_code == 200
    invoice = rejected.json()["invoice"]
    assert invoice["status"] == "REJECTED"
    assert invoice["rejectionReasonCode"] == "DOCUMENT_MISMATCH"
    assert invoice["rejectionReasonDetail"] == "PO 금액과 인보이스 금액을 다시 확인해 주세요."
    assert isinstance(invoice["verificationRejectedAt"], str)

    reviewed = client.post(f"/api/v1/invoices/{invoice_id}/risk-review-request")
    assert reviewed.status_code == 200
    assert reviewed.json()["invoice"]["status"] == "REVIEW_REQUESTED"
    assert isinstance(reviewed.json()["invoice"]["reviewRequestedAt"], str)


def test_complete_frontend_contract_workflow(
    client: TestClient,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    create_response = client.post("/api/v1/invoices", files=contract_files)
    assert create_response.status_code == 201
    created = create_response.json()
    assert set(created) == {"invoice"}
    invoice = created["invoice"]
    invoice_id = invoice["id"]
    assert invoice["status"] == "DOCUMENT_REVIEW_REQUIRED"
    assert len(invoice["documents"]) == 4
    assert {document["type"] for document in invoice["documents"]} == set(contract_files)
    assert invoice["analysis"]["status"] == "COMPLETED"
    assert invoice["invoiceAmount"] == 3
    assert invoice["currency"] == "USD"
    assert invoice["analysis"]["amount"]["value"] == 3
    assert invoice["analysis"]["currency"]["value"] == "USD"
    assert invoice["riskPassport"] is None
    assert invoice["fundingTransaction"] is None
    assert invoice["settlementTransaction"] is None
    assert invoice["settlement"] is None
    assert isinstance(invoice["agentTraces"], list)

    listed = client.get("/api/v1/invoices")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == invoice_id

    verification_response = client.post(f"/api/v1/invoices/{invoice_id}/verification-request")
    assert verification_response.status_code == 200
    verification_invoice = verification_response.json()["invoice"]
    assert verification_invoice["status"] == "BUYER_REVIEW"
    verification_id = verification_invoice["verificationId"]
    requested_at = verification_invoice["verificationRequestedAt"]
    assert isinstance(requested_at, str)

    duplicate_request = client.post(f"/api/v1/invoices/{invoice_id}/verification-request")
    assert duplicate_request.json()["invoice"]["verificationId"] == verification_id
    listed_verification = client.get("/api/v1/verifications").json()["items"][0]
    assert listed_verification == {
        "id": verification_id,
        "invoiceId": invoice_id,
        "status": "PENDING",
        "createdAt": requested_at,
        "rejectionReasonCode": None,
        "rejectionReasonDetail": None,
        "respondedAt": None,
    }
    assert client.get(f"/api/v1/verifications/{verification_id}").json() == {
        "verification": listed_verification
    }

    confirmed = client.post(f"/api/v1/verifications/{verification_id}/confirm")
    assert confirmed.status_code == 200
    offered = confirmed.json()["invoice"]
    assert offered["status"] == "OFFER_READY"
    assert offered["riskPassport"]["eligibility"] == "ELIGIBLE"
    assert 70 <= offered["riskPassport"]["riskScore"] <= 100
    assert offered["riskPassport"]["invoiceFaceValueUsdc"] == 3
    assert offered["riskPassport"]["sourceCurrencyToUsdcRate"] == 1
    assert offered["riskPassport"]["dataCoverageBps"] == 10_000
    assert len(offered["riskPassport"]["scoreFactors"]) == 4
    assert sum(factor["score"] for factor in offered["riskPassport"]["scoreFactors"]) == offered["riskPassport"]["riskScore"]
    assert offered["riskPassport"]["hardGate"]["passed"] is True
    assert len(offered["riskPassport"]["hardGate"]["checks"]) == 8
    terms = offered["riskPassport"]["earlySettlementTerms"]
    assert terms["annualExpectedYieldBps"] == terms["sofrRateBps"] + terms["riskSpreadBps"] + terms["countryLegalSpreadBps"]
    assert terms["purchaseAmountUsdc"] == terms["faceValueUsdc"] - terms["expectedInvestorReturnUsdc"]
    assert terms["supplierExpectedSettlementUsdc"] == terms["purchaseAmountUsdc"] - terms["platformFeeUsdc"]
    assert offered["riskPassport"]["earlySettlementTerms"]["reserveAmountUsdc"] == 0
    assert isinstance(offered["verificationConfirmedAt"], str)

    duplicate_confirm = client.post(f"/api/v1/verifications/{verification_id}/confirm")
    assert duplicate_confirm.json()["invoice"]["status"] == "OFFER_READY"

    accepted = client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={"response": "ACCEPT"},
    )
    assert accepted.status_code == 200
    issued = accepted.json()["invoice"]
    assert issued["status"] == "RWA_ISSUED"
    assert issued["rwaAsset"]["status"] == "ISSUED"
    assert issued["rwaAsset"]["faceValueUsdc"] == 3
    assert issued["rwaAsset"]["issuancePriceUsdc"] == terms["supplierExpectedSettlementUsdc"]
    assert issued["fundingTransaction"] is None

    investor = Keypair()
    policy = {
        "totalInvestmentLimitUsdc": 20_000,
        "perInvoiceLimitUsdc": 20_000,
        "buyerAllowlist": ["Prime Mobility"],
        "minimumRiskScore": 80,
        "maximumRemainingTermDays": 100,
        "expiresAt": "2030-12-31",
    }
    prepared_mandate = client.post(
        "/api/v1/investor/mandates/prepare",
        json={"ownerWalletAddress": str(investor.pubkey()), "policy": policy},
    )
    assert prepared_mandate.status_code == 200
    signature = str(investor.sign_message(prepared_mandate.json()["canonicalMessage"].encode()))
    mandate = client.post(
        "/api/v1/investor/mandates",
        json={
            "ownerWalletAddress": str(investor.pubkey()),
            "policy": policy,
            "signature": signature,
        },
    )
    assert mandate.status_code == 200
    assert mandate.json()["status"] == "ACTIVE"

    prepared_deposit = client.post(
        "/api/v1/investor/vault/deposits/prepare",
        json={"ownerWalletAddress": str(investor.pubkey()), "amountUsdc": terms["supplierExpectedSettlementUsdc"]},
    )
    assert prepared_deposit.status_code == 200
    assert prepared_deposit.json()["vaultAddress"] == "DEMO_AGENT_VAULT"
    deposited = client.post(
        "/api/v1/investor/vault/deposits/confirm",
        json={
            "ownerWalletAddress": str(investor.pubkey()),
            "amountUsdc": terms["supplierExpectedSettlementUsdc"],
            "signature": "mock-deposit-signature-001",
        },
    )
    assert deposited.status_code == 200

    funded = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
    assert funded["status"] == "FUNDED"
    assert funded["fundingTransaction"]["status"] == "CONFIRMED"
    assert funded["fundingTransaction"]["amountUsdc"] == terms["supplierExpectedSettlementUsdc"]
    assert funded["fundingTransaction"]["network"] == "SOLANA_DEVNET"
    assert funded["fundingTransaction"]["sandbox"] is True
    assert funded["rwaAsset"]["status"] == "SOLD"
    assert funded["agentDecision"]["status"] == "EXECUTED"
    funding_signature = funded["fundingTransaction"]["signature"]

    duplicate_accept = client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={"response": "ACCEPT"},
    )
    assert (
        duplicate_accept.json()["invoice"]["fundingTransaction"]["signature"] == funding_signature
    )

    dashboard = client.get("/api/v1/investor/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["outstandingPrincipalUsdc"] == terms["supplierExpectedSettlementUsdc"]

    settled_response = client.post(f"/api/v1/invoices/{invoice_id}/settlement/mock-payment")
    assert settled_response.status_code == 200
    settled = settled_response.json()["invoice"]
    assert settled["status"] == "SETTLED"
    assert settled["settlement"] == {
        "invoiceFaceValueUsdc": terms["faceValueUsdc"],
        "investorSettlementUsdc": terms["faceValueUsdc"] - terms["platformFeeUsdc"],
        "platformFeeUsdc": terms["platformFeeUsdc"],
        "supplierResidualUsdc": 0,
    }
    assert settled["settlementTransaction"]["sandbox"] is True
    settlement_signature = settled["settlementTransaction"]["signature"]

    duplicate_settlement = client.post(f"/api/v1/invoices/{invoice_id}/settlement/mock-payment")
    assert (
        duplicate_settlement.json()["invoice"]["settlementTransaction"]["signature"]
        == settlement_signature
    )


def test_contract_validation_and_sanitized_errors(
    client: TestClient,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    missing_part = dict(contract_files)
    missing_part.pop("CONTRACT")
    response = client.post("/api/v1/invoices", files=missing_part)
    assert response.status_code == 422
    assert "message" in response.json()

    bad_mime = dict(contract_files)
    bad_mime["CONTRACT"] = ("contract.txt", b"unsafe", "text/plain")
    response = client.post("/api/v1/invoices", files=bad_mime)
    assert response.status_code == 400
    assert response.json() == {"message": "CONTRACT 파일은 PDF, JPG, JPEG, PNG만 허용합니다."}

    response = client.get("/api/v1/invoices/INV-404")
    assert response.status_code == 404
    assert response.json() == {"message": "Invoice INV-404를 찾을 수 없습니다."}


def test_upload_limit_is_enforced_before_agent_call(tmp_path: Path) -> None:
    settings = mock_settings(
        tmp_path / "uploads",
        MAX_DOCUMENT_SIZE_BYTES=4,
    )
    with TestClient(create_app(settings=settings)) as client:
        files = {
            part: (f"{part}.pdf", b"12345", "application/pdf")
            for part in (
                "INVOICE",
                "CONTRACT",
                "PURCHASE_ORDER",
                "DELIVERY_PROOF",
            )
        }
        response = client.post("/api/v1/invoices", files=files)
    assert response.status_code == 400
    assert response.json()["message"].startswith("INVOICE")


def test_openapi_documents_exact_contract_fields(client: TestClient) -> None:
    schema = client.get("/api/docs-json").json()
    expected_paths = {
        "/api/v1/auth/login",
            "/api/v1/auth/me",
            "/api/v1/auth/company-profile",
            "/api/v1/auth/embedded-wallet",
            "/api/v1/auth/settlement-wallet",
        "/api/v1/auth/account",
        "/api/v1/onboarding/company",
        "/api/v1/invoices",
            "/api/v1/invoices/{invoiceId}",
            "/api/v1/invoices/{invoiceId}/agent-activity",
        "/api/v1/invoices/{invoiceId}/verification-request",
        "/api/v1/verifications",
        "/api/v1/verifications/{verificationId}",
        "/api/v1/verifications/{verificationId}/confirm",
        "/api/v1/verifications/{verificationId}/reject",
        "/api/v1/invoices/{invoiceId}/risk-review-request",
        "/api/v1/invoices/{invoiceId}/offer-response",
        "/api/v1/investor/dashboard",
        "/api/v1/investor/mandates/prepare",
        "/api/v1/investor/mandates",
        "/api/v1/investor/mandates/active",
        "/api/v1/investor/vault",
        "/api/v1/investor/vault/deposits/prepare",
        "/api/v1/investor/vault/deposits/sponsor",
        "/api/v1/investor/vault/deposits/confirm",
        "/api/v1/supplier/wallet",
        "/api/v1/invoices/{invoiceId}/settlement/mock-payment",
        "/api/v1/invoices/{invoiceId}/buyer-payment/prepare",
        "/api/v1/invoices/{invoiceId}/buyer-payment/confirm",
        "/api/v1/reference/investment-criteria/buyers",
    }
    assert set(schema["paths"]) == expected_paths
    request_schema = schema["paths"]["/api/v1/invoices"]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]["schema"]
    name = request_schema["$ref"].rsplit("/", 1)[-1]
    multipart = schema["components"]["schemas"][name]
    assert set(multipart["properties"]) == {
        "INVOICE",
        "CONTRACT",
        "PURCHASE_ORDER",
        "DELIVERY_PROOF",
    }
    assert set(multipart["required"]) == set(multipart["properties"])


def test_healthz_is_available_without_api_authentication(client: TestClient) -> None:
    for path in ("/healthz", "/api/v1/healthz"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_otp_clock_uses_server_time_and_is_not_cached(client: TestClient) -> None:
    before_ms = int(time.time() * 1000)
    response = client.get("/api/v1/auth/otp-clock")
    after_ms = int(time.time() * 1000)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["expiresInSeconds"] == 300
    assert before_ms <= response.json()["serverTimeMs"] <= after_ms


def test_fixed_demo_accounts_issue_tokens_and_protect_gcp_api(tmp_path: Path) -> None:
    settings = mock_settings(
        tmp_path / "uploads",
        API_AUTH_REQUIRED=True,
        AUTH_TOKEN_SECRET="test-token-secret-that-is-long-enough-for-hmac",
    )
    with TestClient(create_app(settings=settings)) as authenticated_client:
        blocked = authenticated_client.get("/api/v1/invoices")
        assert blocked.status_code == 401

        login = authenticated_client.post(
            "/api/v1/auth/login",
            json={
                "role": "Investor",
                "email": "investor@company.com",
                "password": "investor",
            },
        )
        assert login.status_code == 200
        token = login.json()["accessToken"]
        assert login.json()["role"] == "Investor"

        buyers = authenticated_client.get(
            "/api/v1/reference/investment-criteria/buyers",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert buyers.status_code == 200
        assert [buyer["name"] for buyer in buyers.json()] == [
            "Prime Mobility",
            "Orbit Components",
            "Daon Logistics",
            "Vertex Retail",
        ]

        rejected = authenticated_client.post(
            "/api/v1/auth/login",
            json={
                "role": "Investor",
                "email": "investor@company.com",
                "password": "wrong-password",
            },
        )
        assert rejected.status_code == 401


def test_fixed_demo_accounts_cannot_cross_role_boundaries(tmp_path: Path) -> None:
    settings = mock_settings(
        tmp_path / "uploads",
        API_AUTH_REQUIRED=True,
        AUTH_TOKEN_SECRET="test-token-secret-that-is-long-enough-for-hmac",
    )
    with TestClient(create_app(settings=settings)) as authenticated_client:
        investor_login = authenticated_client.post(
            "/api/v1/auth/login",
            json={
                "role": "Investor",
                "email": "investor@company.com",
                "password": "investor",
            },
        )
        investor_headers = {"Authorization": f"Bearer {investor_login.json()['accessToken']}"}

        supplier_login = authenticated_client.post(
            "/api/v1/auth/login",
            json={
                "role": "Supplier",
                "email": "supplier@company.com",
                "password": "supplier",
            },
        )
        supplier_headers = {"Authorization": f"Bearer {supplier_login.json()['accessToken']}"}

        rejected_upload = authenticated_client.post(
            "/api/v1/invoices",
            headers=investor_headers,
            files={
                part: (f"{part}.pdf", b"%PDF-1.4", "application/pdf")
                for part in ("INVOICE", "CONTRACT", "PURCHASE_ORDER", "DELIVERY_PROOF")
            },
        )
        assert rejected_upload.status_code == 403
        assert authenticated_client.get(
            "/api/v1/investor/dashboard", headers=supplier_headers
        ).status_code == 403

        buyer_login = authenticated_client.post(
            "/api/v1/auth/login",
            json={
                "role": "Buyer",
                "email": "buyer@company.com",
                "password": "buyer",
            },
        )
        buyer_headers = {"Authorization": f"Bearer {buyer_login.json()['accessToken']}"}
        assert (
            authenticated_client.get("/api/v1/invoices", headers=buyer_headers).status_code == 200
        )
        assert (
            authenticated_client.get(
                "/api/v1/invoices", headers=investor_headers
            ).status_code
            == 200
        )
