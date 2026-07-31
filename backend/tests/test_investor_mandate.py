"""InvestorSetupPage collected an AP2 policy that nothing on the server read."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from invoicex_backend.config import BackendSettings
from tests.conftest import mock_settings


def demo_client(settings: BackendSettings) -> TestClient:
    return TestClient(create_app(settings=settings))


def advance_to_offer(client: TestClient) -> str:
    invoice_id = client.post("/api/v1/demo/reset").json()["invoice"]["id"]
    client.post(f"/api/v1/invoices/{invoice_id}/analyze")
    verification_id = client.post(
        f"/api/v1/invoices/{invoice_id}/verification-request"
    ).json()["invoice"]["verificationId"]
    client.post(f"/api/v1/verifications/{verification_id}/confirm")
    return invoice_id


def accept(client: TestClient, invoice_id: str) -> dict[str, object]:
    client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={"response": "ACCEPT"},
    )
    return client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]


def mandate_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "depositUsdc": 50_000,
        "totalLimitUsdc": 50_000,
        "perInvoiceLimitUsdc": 20_000,
        "buyerAllowlist": ["BUYER_PRIME"],
        "minimumRiskScore": 80,
        "maximumTermDays": 120,
        "policyExpiresOn": "2026-12-31",
    }
    body.update(overrides)
    return body


def test_default_mandate_is_served_before_anything_is_saved(tmp_path: Path) -> None:
    with demo_client(mock_settings(tmp_path / "uploads")) as client:
        mandate = client.get("/api/v1/investor/mandate").json()["mandate"]

        assert mandate["status"] == "ACTIVE"
        assert mandate["buyerAllowlist"] == ["BUYER_PRIME"]
        assert mandate["minimumRiskScore"] == 80


def test_saved_mandate_is_returned_and_survives_restart(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    with demo_client(settings) as client:
        saved = client.put(
            "/api/v1/investor/mandate",
            json=mandate_body(depositUsdc=41_000, maximumTermDays=45),
        )

        assert saved.status_code == 200
        assert saved.json()["mandate"]["depositUsdc"] == 41_000

    with demo_client(settings) as client:
        mandate = client.get("/api/v1/investor/mandate").json()["mandate"]
        assert mandate["depositUsdc"] == 41_000
        assert mandate["maximumTermDays"] == 45


def test_dashboard_reflects_the_saved_mandate(tmp_path: Path) -> None:
    with demo_client(mock_settings(tmp_path / "uploads")) as client:
        client.put("/api/v1/investor/mandate", json=mandate_body(depositUsdc=30_000))
        invoice_id = advance_to_offer(client)
        accept(client, invoice_id)

        dashboard = client.get("/api/v1/investor/dashboard").json()

        assert dashboard["outstandingPrincipalUsdc"] == 18_800
        # 30,000 deposited minus the 18,800 now at work.
        assert dashboard["availableVaultUsdc"] == 11_200
        assert dashboard["mandateStatus"] == "ACTIVE"


def test_default_mandate_still_funds_the_happy_path(tmp_path: Path) -> None:
    with demo_client(mock_settings(tmp_path / "uploads")) as client:
        invoice_id = advance_to_offer(client)

        invoice = accept(client, invoice_id)

        assert invoice["status"] == "FUNDED"
        assert invoice["fundingTransaction"]["amountUsdc"] == 18_800


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"minimumRiskScore": 95}, "Risk Score"),
        ({"perInvoiceLimitUsdc": 10_000}, "건별 한도"),
        ({"totalLimitUsdc": 1_000}, "총 투자 한도"),
        ({"depositUsdc": 5_000}, "Vault 예치 잔액"),
        ({"buyerAllowlist": ["BUYER_OTHER"]}, "허용 목록"),
        ({"maximumTermDays": 10}, "잔존 만기"),
        ({"policyExpiresOn": "2020-01-01"}, "만료"),
        ({"status": "DRAFT"}, "활성"),
    ],
)
def test_each_mandate_field_can_block_funding(
    tmp_path: Path,
    overrides: dict[str, object],
    reason: str,
) -> None:
    """Every input on InvestorSetupPage must actually change what gets bought."""

    with demo_client(mock_settings(tmp_path / "uploads")) as client:
        client.put("/api/v1/investor/mandate", json=mandate_body(**overrides))
        invoice_id = advance_to_offer(client)

        invoice = accept(client, invoice_id)

        assert invoice["status"] == "BLOCKED"
        assert invoice["fundingTransaction"] is None
        blocked_trace = invoice["agentTraces"][-1]
        assert blocked_trace["status"] == "FAILED"
        assert reason in blocked_trace["summary"]


def test_a_mandate_violation_never_reaches_offer_ready(tmp_path: Path) -> None:
    """The supplier must not be shown an offer the Treasury Agent will refuse.

    The mandate used to be checked only at execution, so a tightened limit still
    advertised the full offer and only failed after the supplier accepted it.
    """

    with demo_client(mock_settings(tmp_path / "uploads")) as client:
        client.put(
            "/api/v1/investor/mandate",
            json=mandate_body(perInvoiceLimitUsdc=10_000),
        )

        invoice_id = advance_to_offer(client)

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "BLOCKED"
        assert "건별 한도" in invoice["agentTraces"][-1]["summary"]
        # The Risk Passport is still delivered so the UI can explain the refusal.
        assert invoice["riskPassport"]["suggestedAdvanceAmountUsdc"] == 18_800
        # And accepting is refused outright rather than failing after the fact.
        refused = client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )
        assert refused.status_code == 409


def test_a_mandate_that_allows_the_invoice_still_offers_it(tmp_path: Path) -> None:
    with demo_client(mock_settings(tmp_path / "uploads")) as client:
        client.put("/api/v1/investor/mandate", json=mandate_body())

        invoice_id = advance_to_offer(client)

        invoice = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert invoice["status"] == "OFFER_READY"


def test_funding_consumes_the_vault_for_the_next_invoice(tmp_path: Path) -> None:
    """Outstanding principal must count against the limits, not just be displayed."""

    settings = mock_settings(tmp_path / "uploads")
    with demo_client(settings) as client:
        client.put(
            "/api/v1/investor/mandate",
            json=mandate_body(depositUsdc=25_000, totalLimitUsdc=25_000),
        )
        first = advance_to_offer(client)
        assert accept(client, first)["status"] == "FUNDED"
        assert client.get("/api/v1/investor/dashboard").json()[
            "availableVaultUsdc"
        ] == 6_200

        # A second invoice needs another 18,800, which no longer fits.
        service = client.app.state.invoice_service
        second = service._new_invoice("INV-2026-999", service.get_invoice(first).status)
        second.risk_passport = service.get_invoice(first).risk_passport
        assert (
            service._mandate_policy.rejection_reason(
                second,
                service.get_mandate(),
                outstanding_usdc=service._outstanding_principal(),
            )
            == "Mandate 총 투자 한도를 초과합니다."
        )


def test_mandate_rejects_an_unknown_field(tmp_path: Path) -> None:
    with demo_client(mock_settings(tmp_path / "uploads")) as client:
        response = client.put(
            "/api/v1/investor/mandate",
            json=mandate_body(unexpected="value"),
        )

        assert response.status_code == 422


def test_mandate_rejects_an_out_of_range_score(tmp_path: Path) -> None:
    with demo_client(mock_settings(tmp_path / "uploads")) as client:
        response = client.put(
            "/api/v1/investor/mandate",
            json=mandate_body(minimumRiskScore=140),
        )

        assert response.status_code == 422
