"""The Buyer checklist was collected in the UI and thrown away before reaching us."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from tests.conftest import mock_settings

POSITIVE = {
    "transaction": "MATCH",
    "supplier": "MATCH",
    "amount": "MATCH",
    "dueDate": "MATCH",
    "delivery": "MATCH",
    "dispute": "MATCH",
}


def buyer_review(tmp_path: Path) -> tuple[TestClient, str, str]:
    client = TestClient(create_app(settings=mock_settings(tmp_path / "uploads")))
    client.__enter__()
    invoice_id = client.post("/api/v1/demo/reset").json()["invoice"]["id"]
    client.post(f"/api/v1/invoices/{invoice_id}/analyze")
    verification_id = client.post(
        f"/api/v1/invoices/{invoice_id}/verification-request"
    ).json()["invoice"]["verificationId"]
    return client, invoice_id, verification_id


def test_demo_happy_path_never_rejects(tmp_path: Path) -> None:
    """The demo sends no body, and that must always reach OFFER_READY."""

    client, invoice_id, verification_id = buyer_review(tmp_path)
    with client:
        confirmed = client.post(f"/api/v1/verifications/{verification_id}/confirm")

        assert confirmed.status_code == 200
        assert confirmed.json()["invoice"]["status"] == "RISK_ASSESSING"
        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "OFFER_READY"
        assert invoice["riskPassport"]["eligibility"] == "ELIGIBLE"
        assert invoice["riskPassport"]["suggestedAdvanceAmountUsdc"] == 18_800


def test_all_positive_checklist_matches_the_empty_body(tmp_path: Path) -> None:
    client, invoice_id, verification_id = buyer_review(tmp_path)
    with client:
        client.post(
            f"/api/v1/verifications/{verification_id}/confirm",
            json={"checklist": POSITIVE},
        )

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "OFFER_READY"
        assert invoice["riskPassport"]["eligibility"] == "ELIGIBLE"


def test_transaction_row_is_pinned_positive(tmp_path: Path) -> None:
    """Synthetic demo data cannot legitimately be "the transaction does not exist"."""

    client, invoice_id, verification_id = buyer_review(tmp_path)
    with client:
        client.post(
            f"/api/v1/verifications/{verification_id}/confirm",
            json={"checklist": {**POSITIVE, "transaction": "MISMATCH"}},
        )

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "OFFER_READY"
        assert invoice["riskPassport"]["eligibility"] == "ELIGIBLE"
        stored = client.get(
            f"/api/v1/verifications/{verification_id}"
        ).json()["verification"]
        assert stored["status"] == "CONFIRMED"
        assert stored["checklist"]["transaction"] == "MATCH"


def test_checklist_is_recorded_on_the_verification(tmp_path: Path) -> None:
    client, _, verification_id = buyer_review(tmp_path)
    with client:
        client.post(
            f"/api/v1/verifications/{verification_id}/confirm",
            json={"checklist": {**POSITIVE, "amount": "MISMATCH"}},
        )

        stored = client.get(
            f"/api/v1/verifications/{verification_id}"
        ).json()["verification"]
        assert stored["checklist"]["amount"] == "MISMATCH"
        assert stored["checklist"]["supplier"] == "MATCH"


def test_reported_mismatch_downgrades_eligibility(tmp_path: Path) -> None:
    client, invoice_id, verification_id = buyer_review(tmp_path)
    with client:
        client.post(
            f"/api/v1/verifications/{verification_id}/confirm",
            json={"checklist": {**POSITIVE, "amount": "MISMATCH"}},
        )

        passport = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"][
            "riskPassport"
        ]
        assert passport["eligibility"] == "REVIEW_REQUIRED"
        assert passport["suggestedAdvanceAmountUsdc"] is None
        titles = [factor["title"] for factor in passport["riskFactors"]]
        assert "구매기업이 불일치를 보고함" in titles


def test_reported_dispute_blocks_the_offer(tmp_path: Path) -> None:
    client, invoice_id, verification_id = buyer_review(tmp_path)
    with client:
        client.post(
            f"/api/v1/verifications/{verification_id}/confirm",
            json={"checklist": {**POSITIVE, "dispute": "MISMATCH"}},
        )

        passport = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"][
            "riskPassport"
        ]
        assert passport["eligibility"] == "BLOCKED"
        assert passport["suggestedAdvanceAmountUsdc"] is None
        dispute = next(
            factor
            for factor in passport["riskFactors"]
            if factor["title"] == "분쟁 또는 결제 보류"
        )
        assert dispute["severity"] == "HIGH"


def test_blocked_offer_cannot_be_funded(tmp_path: Path) -> None:
    """A disputed invoice must not reach the supplier's wallet."""

    client, invoice_id, verification_id = buyer_review(tmp_path)
    with client:
        client.post(
            f"/api/v1/verifications/{verification_id}/confirm",
            json={"checklist": {**POSITIVE, "dispute": "MISMATCH"}},
        )
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "BLOCKED"
        assert invoice["fundingTransaction"] is None


def test_checklist_survives_restart(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    with TestClient(create_app(settings=settings)) as client:
        invoice_id = client.post("/api/v1/demo/reset").json()["invoice"]["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/analyze")
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(
            f"/api/v1/verifications/{verification_id}/confirm",
            json={"checklist": {**POSITIVE, "delivery": "MISMATCH"}},
        )

    with TestClient(create_app(settings=settings)) as client:
        stored = client.get(
            f"/api/v1/verifications/{verification_id}"
        ).json()["verification"]
        assert stored["checklist"]["delivery"] == "MISMATCH"


def test_unknown_checklist_row_is_rejected(tmp_path: Path) -> None:
    client, _, verification_id = buyer_review(tmp_path)
    with client:
        response = client.post(
            f"/api/v1/verifications/{verification_id}/confirm",
            json={"checklist": {**POSITIVE, "unexpected": "MATCH"}},
        )

        assert response.status_code == 422
