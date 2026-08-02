from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from tests.conftest import mock_settings


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
    assert {document["type"] for document in invoice["documents"]} == set(
        contract_files
    )
    assert invoice["analysis"]["status"] == "COMPLETED"
    assert invoice["analysis"]["amountKrw"]["value"] == 20_000_000
    assert invoice["riskPassport"] is None
    assert invoice["fundingTransaction"] is None
    assert invoice["settlementTransaction"] is None
    assert invoice["settlement"] is None
    assert isinstance(invoice["agentTraces"], list)

    listed = client.get("/api/v1/invoices")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == invoice_id

    verification_response = client.post(
        f"/api/v1/invoices/{invoice_id}/verification-request"
    )
    assert verification_response.status_code == 200
    verification_invoice = verification_response.json()["invoice"]
    assert verification_invoice["status"] == "BUYER_REVIEW"
    verification_id = verification_invoice["verificationId"]

    duplicate_request = client.post(
        f"/api/v1/invoices/{invoice_id}/verification-request"
    )
    assert duplicate_request.json()["invoice"]["verificationId"] == verification_id
    assert client.get("/api/v1/verifications").json() == {
        "items": [
            {
                "id": verification_id,
                "invoiceId": invoice_id,
                "status": "PENDING",
            }
        ]
    }
    assert client.get(f"/api/v1/verifications/{verification_id}").json() == {
        "verification": {
            "id": verification_id,
            "invoiceId": invoice_id,
            "status": "PENDING",
        }
    }

    confirmed = client.post(f"/api/v1/verifications/{verification_id}/confirm")
    assert confirmed.status_code == 200
    offered = confirmed.json()["invoice"]
    assert offered["status"] == "OFFER_READY"
    assert offered["riskPassport"]["eligibility"] == "ELIGIBLE"
    assert offered["riskPassport"]["riskScore"] == 86
    assert offered["riskPassport"]["suggestedAdvanceRateBps"] == 9_400
    assert offered["riskPassport"]["suggestedAdvanceAmountUsdc"] == 18_800
    assert offered["rwa"] is not None
    assert offered["rwa"]["invoiceId"] == invoice_id
    assert offered["rwa"]["amount"] == 1
    assert offered["rwa"]["decimals"] == 0
    assert offered["rwa"]["network"] == "SOLANA_DEVNET"
    assert offered["rwa"]["status"] == "CONFIRMED"
    assert offered["rwa"]["provider"] == "MOCK"
    assert offered["rwa"]["mintAddress"]
    assert offered["rwa"]["mintExplorerUrl"] == (
        f"https://explorer.solana.com/address/{offered['rwa']['mintAddress']}"
        "?cluster=devnet"
    )

    duplicate_confirm = client.post(
        f"/api/v1/verifications/{verification_id}/confirm"
    )
    assert duplicate_confirm.json()["invoice"]["status"] == "OFFER_READY"

    accepted = client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={
            "response": "ACCEPT",
            "supplierWalletAddress": "So11111111111111111111111111111111111111112",
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["invoice"]["status"] == "FUNDING"

    funded = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
    assert funded["status"] == "FUNDED"
    assert funded["fundingTransaction"]["status"] == "CONFIRMED"
    assert funded["fundingTransaction"]["amountUsdc"] == 18_800
    assert funded["fundingTransaction"]["network"] == "SOLANA_DEVNET"
    assert funded["fundingTransaction"]["sandbox"] is True
    assert funded["fundingTransaction"]["toAddress"] == (
        "So11111111111111111111111111111111111111112"
    )
    funding_signature = funded["fundingTransaction"]["signature"]

    duplicate_accept = client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={"response": "ACCEPT"},
    )
    assert (
        duplicate_accept.json()["invoice"]["fundingTransaction"]["signature"]
        == funding_signature
    )

    dashboard = client.get("/api/v1/investor/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["outstandingPrincipalUsdc"] == 18_800

    settled_response = client.post(
        f"/api/v1/invoices/{invoice_id}/settlement/mock-payment"
    )
    assert settled_response.status_code == 200
    settled = settled_response.json()["invoice"]
    assert settled["status"] == "SETTLED"
    assert settled["settlement"] == {
        "invoiceFaceValueUsdc": 20_000,
        "investorSettlementUsdc": 19_800,
        "platformFeeUsdc": 200,
        "supplierResidualUsdc": 0,
    }
    assert settled["settlementTransaction"]["sandbox"] is True
    settlement_signature = settled["settlementTransaction"]["signature"]

    duplicate_settlement = client.post(
        f"/api/v1/invoices/{invoice_id}/settlement/mock-payment"
    )
    assert (
        duplicate_settlement.json()["invoice"]["settlementTransaction"]["signature"]
        == settlement_signature
    )


def test_privy_devnet_caps_the_demo_transfer_to_connected_wallet(
    client: TestClient,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    invoice = client.post("/api/v1/invoices", files=contract_files).json()["invoice"]
    invoice_id = invoice["id"]
    verification = client.post(
        f"/api/v1/invoices/{invoice_id}/verification-request"
    ).json()["invoice"]
    client.post(f"/api/v1/verifications/{verification['verificationId']}/confirm")

    service = client.app.state.invoice_service
    service._solana.mode = "privy"
    service._available_vault_usdc = 0
    supplier_wallet = "So11111111111111111111111111111111111111112"
    blocked = client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={
            "response": "ACCEPT",
            "supplierWalletAddress": supplier_wallet,
        },
    )
    assert blocked.status_code == 409

    investor_wallet = "Vote111111111111111111111111111111111111111"
    prepared = client.post(
        "/api/v1/investor/deposits/prepare",
        json={"investorWalletAddress": investor_wallet, "amountUsdc": 20},
    )
    assert prepared.status_code == 200
    preparation = prepared.json()
    assert preparation["investorWalletAddress"] == investor_wallet
    assert preparation["amountUsdc"] == 20
    confirmed = client.post(
        "/api/v1/investor/deposits/confirm",
        json={
            "referenceId": preparation["referenceId"],
            "signature": "demo-investor-deposit-signature",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "CONFIRMED"
    repeated = client.post(
        "/api/v1/investor/deposits/confirm",
        json={
            "referenceId": preparation["referenceId"],
            "signature": "demo-investor-deposit-signature",
        },
    )
    assert repeated.status_code == 200
    replay_preparation = client.post(
        "/api/v1/investor/deposits/prepare",
        json={"investorWalletAddress": investor_wallet, "amountUsdc": 20},
    ).json()
    replayed = client.post(
        "/api/v1/investor/deposits/confirm",
        json={
            "referenceId": replay_preparation["referenceId"],
            "signature": "demo-investor-deposit-signature",
        },
    )
    assert replayed.status_code == 409
    assert client.get("/api/v1/investor/dashboard").json()[
        "availableVaultUsdc"
    ] == 20

    accepted = client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={
            "response": "ACCEPT",
            "supplierWalletAddress": supplier_wallet,
        },
    )

    assert accepted.status_code == 200
    funded = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
    assert funded["riskPassport"]["suggestedAdvanceAmountUsdc"] == 18_800
    assert funded["fundingTransaction"]["amountUsdc"] == 1
    assert funded["fundingTransaction"]["toAddress"] == supplier_wallet
    assert client.get("/api/v1/investor/dashboard").json()[
        "outstandingPrincipalUsdc"
    ] == 1
    assert client.get("/api/v1/investor/dashboard").json()[
        "availableVaultUsdc"
    ] == 19


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
    assert response.json() == {
        "message": "CONTRACT 파일은 PDF, JPG, JPEG, PNG만 허용합니다."
    }

    response = client.get("/api/v1/invoices/INV-404")
    assert response.status_code == 404
    assert response.json() == {
        "message": "Invoice INV-404를 찾을 수 없습니다."
    }


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
        "/api/v1/invoices",
        "/api/v1/invoices/{invoiceId}",
        "/api/v1/invoices/{invoiceId}/verification-request",
        "/api/v1/verifications",
        "/api/v1/verifications/{verificationId}",
        "/api/v1/verifications/{verificationId}/confirm",
        "/api/v1/invoices/{invoiceId}/offer-response",
        "/api/v1/investor/dashboard",
        "/api/v1/investor/deposits/prepare",
        "/api/v1/investor/deposits/confirm",
        "/api/v1/investor/mandate/prepare",
        "/api/v1/investor/mandate/activate",
        "/api/v1/investor/mandate",
        "/api/v1/investor/mandate/emergency-stop",
        "/api/v1/invoices/{invoiceId}/settlement/mock-payment",
    }
    assert set(schema["paths"]) == expected_paths
    request_schema = schema["paths"]["/api/v1/invoices"]["post"]["requestBody"][
        "content"
    ]["multipart/form-data"]["schema"]
    name = request_schema["$ref"].rsplit("/", 1)[-1]
    multipart = schema["components"]["schemas"][name]
    assert set(multipart["properties"]) == {
        "INVOICE",
        "CONTRACT",
        "PURCHASE_ORDER",
        "DELIVERY_PROOF",
    }
    assert set(multipart["required"]) == set(multipart["properties"])
