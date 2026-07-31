"""The Buyer screen's "수정 요청" button had no server call behind it."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from tests.conftest import mock_settings


def buyer_review_client(tmp_path: Path) -> tuple[TestClient, str, str]:
    client = TestClient(create_app(settings=mock_settings(tmp_path / "uploads")))
    client.__enter__()
    invoice_id = client.post("/api/v1/demo/reset").json()["invoice"]["id"]
    client.post(f"/api/v1/invoices/{invoice_id}/analyze")
    verification_id = client.post(
        f"/api/v1/invoices/{invoice_id}/verification-request"
    ).json()["invoice"]["verificationId"]
    return client, invoice_id, verification_id


def test_revision_request_moves_both_aggregates(tmp_path: Path) -> None:
    client, invoice_id, verification_id = buyer_review_client(tmp_path)
    with client:
        response = client.post(
            f"/api/v1/verifications/{verification_id}/revision-request"
        )

        assert response.status_code == 200
        invoice = response.json()["invoice"]
        assert invoice["status"] == "REVISION_REQUESTED"
        assert invoice["agentTraces"][-1]["status"] == "FAILED"
        verification = client.get(
            f"/api/v1/verifications/{verification_id}"
        ).json()["verification"]
        assert verification["status"] == "REVISION_REQUESTED"


def test_revision_request_is_idempotent(tmp_path: Path) -> None:
    client, _, verification_id = buyer_review_client(tmp_path)
    with client:
        first = client.post(f"/api/v1/verifications/{verification_id}/revision-request")
        again = client.post(f"/api/v1/verifications/{verification_id}/revision-request")

        assert again.status_code == 200
        assert again.json()["invoice"]["status"] == "REVISION_REQUESTED"
        assert len(again.json()["invoice"]["agentTraces"]) == len(
            first.json()["invoice"]["agentTraces"]
        )


def test_revision_request_blocks_a_later_confirm(tmp_path: Path) -> None:
    client, _, verification_id = buyer_review_client(tmp_path)
    with client:
        client.post(f"/api/v1/verifications/{verification_id}/revision-request")

        conflict = client.post(f"/api/v1/verifications/{verification_id}/confirm")

        assert conflict.status_code == 409


def test_confirm_blocks_a_later_revision_request(tmp_path: Path) -> None:
    client, _, verification_id = buyer_review_client(tmp_path)
    with client:
        client.post(f"/api/v1/verifications/{verification_id}/confirm")

        conflict = client.post(
            f"/api/v1/verifications/{verification_id}/revision-request"
        )

        assert conflict.status_code == 409


def test_revision_request_survives_restart(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    with TestClient(create_app(settings=settings)) as client:
        invoice_id = client.post("/api/v1/demo/reset").json()["invoice"]["id"]
        client.post(f"/api/v1/invoices/{invoice_id}/analyze")
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/revision-request")

    with TestClient(create_app(settings=settings)) as client:
        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "REVISION_REQUESTED"


def test_revision_request_reports_a_missing_verification(tmp_path: Path) -> None:
    with TestClient(create_app(settings=mock_settings(tmp_path / "uploads"))) as client:
        response = client.post("/api/v1/verifications/VER-404/revision-request")

        assert response.status_code == 404
