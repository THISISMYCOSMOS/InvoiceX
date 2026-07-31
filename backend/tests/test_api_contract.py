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
    accepted = created["invoice"]
    invoice_id = accepted["id"]
    # The upload returns before the Document Agent runs; the frontend polls.
    assert accepted["status"] == "DOCUMENT_ANALYZING"
    assert accepted["analysis"] is None
    assert len(accepted["documents"]) == 4
    assert {document["type"] for document in accepted["documents"]} == set(
        contract_files
    )

    invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
    assert invoice["status"] == "DOCUMENT_REVIEW_REQUIRED"
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
                "checklist": None,
            }
        ]
    }
    assert client.get(f"/api/v1/verifications/{verification_id}").json() == {
        "verification": {
            "id": verification_id,
            "invoiceId": invoice_id,
            "status": "PENDING",
            "checklist": None,
        }
    }

    confirmed = client.post(f"/api/v1/verifications/{verification_id}/confirm")
    assert confirmed.status_code == 200
    # Confirm returns before the Risk Agent runs; the frontend polls again.
    assert confirmed.json()["invoice"]["status"] == "RISK_ASSESSING"
    assert confirmed.json()["invoice"]["riskPassport"] is None

    offered = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
    assert offered["status"] == "OFFER_READY"
    assert offered["riskPassport"]["eligibility"] == "ELIGIBLE"
    assert offered["riskPassport"]["riskScore"] == 86
    assert offered["riskPassport"]["suggestedAdvanceRateBps"] == 9_400
    assert offered["riskPassport"]["suggestedAdvanceAmountUsdc"] == 18_800

    duplicate_confirm = client.post(
        f"/api/v1/verifications/{verification_id}/confirm"
    )
    assert duplicate_confirm.json()["invoice"]["status"] == "OFFER_READY"

    accepted = client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={"response": "ACCEPT"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["invoice"]["status"] == "FUNDING"

    funded = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
    assert funded["status"] == "FUNDED"
    assert funded["fundingTransaction"]["status"] == "CONFIRMED"
    assert funded["fundingTransaction"]["amountUsdc"] == 18_800
    assert funded["fundingTransaction"]["network"] == "SOLANA_DEVNET"
    assert funded["fundingTransaction"]["sandbox"] is True
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
        "/api/v1/invoices/{invoiceId}/settlement/mock-payment",
        # Operations the frontend adapter calls but the contract draft omitted.
        "/api/v1/demo/reset",
        "/api/v1/invoices/{invoiceId}/analyze",
        "/api/v1/invoices/{invoiceId}/funding",
        "/api/v1/verifications/{verificationId}/revision-request",
        "/api/v1/invoices/{invoiceId}/settlement",
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
