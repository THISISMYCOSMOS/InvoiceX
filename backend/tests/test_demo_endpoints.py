"""Endpoints the frontend adapter calls but the contract draft never defined."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from tests.conftest import mock_settings


def demo_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(settings=mock_settings(tmp_path / "uploads")))


def test_reset_returns_a_draft_invoice(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        response = client.post("/api/v1/demo/reset")

        assert response.status_code == 200
        invoice = response.json()["invoice"]
        assert invoice["status"] == "DRAFT"
        assert invoice["documents"] == []
        assert invoice["analysis"] is None
        assert client.get("/api/v1/invoices").json()["items"][0]["id"] == invoice["id"]


def test_reset_clears_previous_invoices(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    with demo_client(tmp_path) as client:
        client.post("/api/v1/invoices", files=contract_files)
        client.post("/api/v1/invoices", files=contract_files)
        assert len(client.get("/api/v1/invoices").json()["items"]) == 2

        seeded = client.post("/api/v1/demo/reset").json()["invoice"]

        items = client.get("/api/v1/invoices").json()["items"]
        assert [item["id"] for item in items] == [seeded["id"]]
        assert client.get("/api/v1/verifications").json() == {"items": []}


def test_analyze_runs_the_seeded_documents(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        seeded = client.post("/api/v1/demo/reset").json()["invoice"]

        accepted = client.post(f"/api/v1/invoices/{seeded['id']}/analyze")

        assert accepted.status_code == 200
        assert accepted.json()["invoice"]["status"] == "DOCUMENT_ANALYZING"
        analyzed = client.get(f"/api/v1/invoices/{seeded['id']}").json()["invoice"]
        assert analyzed["status"] == "DOCUMENT_REVIEW_REQUIRED"
        assert len(analyzed["documents"]) == 4
        assert analyzed["analysis"]["amountKrw"]["value"] == 20_000_000


def test_analyze_rejects_a_non_draft_invoice(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        seeded = client.post("/api/v1/demo/reset").json()["invoice"]
        client.post(f"/api/v1/invoices/{seeded['id']}/analyze")

        conflict = client.post(f"/api/v1/invoices/{seeded['id']}/analyze")

        assert conflict.status_code == 409
        assert "DRAFT" in conflict.json()["message"]


def test_analyze_reports_a_missing_invoice(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        assert client.post("/api/v1/invoices/INV-404/analyze").status_code == 404


def test_funding_endpoint_completes_a_funding_invoice(tmp_path: Path) -> None:
    """DemoControlPage enables this button only while the invoice is FUNDING."""

    with demo_client(tmp_path) as client:
        seeded = client.post("/api/v1/demo/reset").json()["invoice"]
        invoice_id = seeded["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/analyze")
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/confirm")
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )

        funded = client.post(f"/api/v1/invoices/{invoice_id}/funding")

        assert funded.status_code == 200
        invoice = funded.json()["invoice"]
        assert invoice["status"] == "FUNDED"
        assert invoice["fundingTransaction"]["amountUsdc"] == 18_800


def test_real_devnet_mode_caps_only_the_onchain_demo_transfer(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        seeded = client.post("/api/v1/demo/reset").json()["invoice"]
        invoice_id = seeded["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/analyze")
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/confirm")

        # Exercise the real-mode service branch with the deterministic test gateway.
        service = client.app.state.invoice_service
        service._solana.mode = "privy"
        supplier_wallet = "So11111111111111111111111111111111111111112"
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={
                "response": "ACCEPT",
                "supplierWalletAddress": supplier_wallet,
            },
        )

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["riskPassport"]["suggestedAdvanceAmountUsdc"] == 18_800
        assert invoice["fundingTransaction"]["amountUsdc"] == 1
        assert invoice["fundingTransaction"]["toAddress"] == supplier_wallet
        assert client.get("/api/v1/investor/dashboard").json()[
            "outstandingPrincipalUsdc"
        ] == 1


def test_funding_endpoint_is_idempotent(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        seeded = client.post("/api/v1/demo/reset").json()["invoice"]
        invoice_id = seeded["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/analyze")
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/confirm")
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )
        first = client.post(f"/api/v1/invoices/{invoice_id}/funding").json()["invoice"]

        again = client.post(f"/api/v1/invoices/{invoice_id}/funding").json()["invoice"]

        assert again["status"] == "FUNDED"
        assert (
            again["fundingTransaction"]["signature"]
            == first["fundingTransaction"]["signature"]
        )


def test_dashboard_reports_amounts_due_within_thirty_days(tmp_path: Path) -> None:
    """The frontend falls back to a fake 72,840 when this field is absent."""

    with demo_client(tmp_path) as client:
        empty = client.get("/api/v1/investor/dashboard").json()
        assert empty["dueWithin30DaysUsdc"] == 0

        seeded = client.post("/api/v1/demo/reset").json()["invoice"]
        invoice_id = seeded["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/analyze")
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/confirm")
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )

        dashboard = client.get("/api/v1/investor/dashboard").json()

        assert dashboard["outstandingPrincipalUsdc"] == 18_800
        # The seed invoice matures on 2026-10-30, well beyond the 30 day window.
        assert dashboard["dueWithin30DaysUsdc"] == 0


def test_dashboard_counts_an_invoice_maturing_inside_the_window(
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime, timedelta

    with demo_client(tmp_path) as client:
        seeded = client.post("/api/v1/demo/reset").json()["invoice"]
        invoice_id = seeded["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/analyze")
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/confirm")
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )
        service = client.app.state.invoice_service
        soon = (datetime.now(UTC) + timedelta(days=10)).date().isoformat()
        service._invoices[invoice_id].due_date = soon

        dashboard = client.get("/api/v1/investor/dashboard").json()

        assert dashboard["dueWithin30DaysUsdc"] == 18_800


def test_unparseable_due_date_does_not_break_the_dashboard(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        seeded = client.post("/api/v1/demo/reset").json()["invoice"]
        invoice_id = seeded["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/analyze")
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/confirm")
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )
        service = client.app.state.invoice_service
        service._invoices[invoice_id].due_date = "만기일 미정"

        dashboard = client.get("/api/v1/investor/dashboard")

        assert dashboard.status_code == 200
        assert dashboard.json()["dueWithin30DaysUsdc"] == 0
