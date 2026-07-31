"""Every BLOCKED invoice must carry a reason the frontend can show."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from tests.conftest import mock_settings
from tests.test_investor_mandate import advance_to_offer, mandate_body


def demo_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(settings=mock_settings(tmp_path / "uploads")))


def test_declining_the_offer_records_why(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        invoice_id = advance_to_offer(client)

        declined = client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "DECLINE"},
        ).json()["invoice"]

        assert declined["status"] == "BLOCKED"
        trace = declined["agentTraces"][-1]
        assert trace["status"] == "FAILED"
        assert "거절" in trace["summary"]


def test_mandate_rejection_records_why(tmp_path: Path) -> None:
    with demo_client(tmp_path) as client:
        client.put(
            "/api/v1/investor/mandate",
            json=mandate_body(buyerAllowlist=["BUYER_OTHER"]),
        )
        invoice_id = advance_to_offer(client)
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "BLOCKED"
        assert "AP2 Mandate 차단" in invoice["agentTraces"][-1]["summary"]


def test_missing_advance_terms_record_why(tmp_path: Path) -> None:
    """A passport without advance terms is refused by the mandate gate first.

    complete_funding keeps a second guard for the same condition, but the
    mandate check reaches it earlier, so this is the reason a user actually sees.
    """

    with demo_client(tmp_path) as client:
        invoice_id = advance_to_offer(client)
        service = client.app.state.invoice_service
        passport = service._invoices[invoice_id].risk_passport
        assert passport is not None
        passport.suggested_advance_amount_usdc = None

        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "BLOCKED"
        trace = invoice["agentTraces"][-1]
        assert trace["status"] == "FAILED"
        assert "Mandate" in trace["summary"]
        assert invoice["fundingTransaction"] is None


def test_no_blocked_invoice_is_left_without_a_failed_trace(tmp_path: Path) -> None:
    """Guard against a future branch that blocks silently again."""

    with demo_client(tmp_path) as client:
        invoice_id = advance_to_offer(client)
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "DECLINE"},
        )

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "BLOCKED"
        assert any(trace["status"] == "FAILED" for trace in invoice["agentTraces"])
