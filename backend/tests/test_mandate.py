"""Investor Mandate signing, persistence, and Treasury policy enforcement."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from solders.keypair import Keypair

from invoicex_backend.agents import create_agent_gateway
from invoicex_backend.errors import NotFoundError, StateConflictError
from invoicex_backend.models import (
    InvestorMandate,
    InvestorMandateDraftRequest,
    Invoice,
    InvoiceParty,
    InvoiceStatus,
    MandateStatus,
    PositiveFactor,
    RiskEligibility,
    RiskFactor,
    RiskPassport,
)
from invoicex_backend.policy import TreasuryMandatePolicy
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import create_solana_gateway
from invoicex_backend.storage import LocalDocumentStorage
from tests.conftest import mock_settings
from tests.test_firebase_adapters import FakeFirestoreClient, _investor_service

TODAY = date(2026, 8, 2)


def _mandate_draft(**overrides: object) -> InvestorMandateDraftRequest:
    values: dict[str, object] = {
        "investor_wallet_address": "99HjRok4PZoX16d7Zz88S3EW4yjTDaHXJ492GaMJHD1U",
        "total_outstanding_limit_usdc": 100_000,
        "per_invoice_limit_usdc": 20_000,
        "daily_new_investment_limit_usdc": 50_000,
        "buyer_allowlist": [],
        "excluded_buyer_ids": [],
        "max_buyer_concentration_bps": 10_000,
        "min_risk_score": 80,
        "max_remaining_tenor_days": 120,
        "max_advance_rate_bps": 9_500,
        "min_target_net_yield_bps": 100,
        "valid_from": "2026-01-01",
        "valid_until": "2026-12-31",
        "halt_new_investment_on_overdue": True,
        "emergency_stopped": False,
    }
    values.update(overrides)
    return InvestorMandateDraftRequest(**values)


def _mandate(**overrides: object) -> InvestorMandate:
    draft = _mandate_draft(**{k: v for k, v in overrides.items() if k != "status"})
    return InvestorMandate(
        id="MANDATE-2026-001",
        version=1,
        status=overrides.get("status", MandateStatus.ACTIVE),
        **draft.model_dump(),
    )


def _invoice(**overrides: object) -> Invoice:
    passport = overrides.pop(
        "risk_passport",
        RiskPassport(
            invoice_id="INV-2026-001",
            eligibility=RiskEligibility.ELIGIBLE,
            risk_score=86,
            positive_factors=[PositiveFactor(title="t", description="d")],
            risk_factors=[RiskFactor(severity="LOW", title="t", description="d")],
            suggested_advance_rate_bps=9_400,
            suggested_advance_amount_usdc=18_800,
        ),
    )
    values: dict[str, object] = {
        "id": "INV-2026-001",
        "supplier": InvoiceParty(id="SUPPLIER_ALPHA", name="Alpha Components"),
        "buyer": InvoiceParty(id="BUYER_PRIME", name="Prime Mobility"),
        "investor": InvoiceParty(id="INVESTOR_NOVA", name="Nova Capital"),
        "invoice_amount_krw": 20_000_000,
        "issue_date": "2026-07-01",
        "due_date": "2026-10-01",
        "delivery_date": "2026-06-25",
        "contract_number": "CONTRACT-001",
        "purchase_order_number": "PO-001",
        "status": InvoiceStatus.OFFER_READY,
        "verification_id": "VER-2026-001",
        "documents": [],
        "analysis": None,
        "risk_passport": passport,
        "funding_transaction": None,
        "settlement_transaction": None,
        "rwa": None,
        "settlement": None,
        "agent_traces": [],
    }
    values.update(overrides)
    return Invoice(**values)


def _policy(**overrides: object) -> TreasuryMandatePolicy:
    settings = mock_settings(Path("unused"), **overrides)
    return TreasuryMandatePolicy(settings)


# ---------------------------------------------------------------------------
# canonical_message()
# ---------------------------------------------------------------------------


def test_canonical_message_is_deterministic_regardless_of_construction_order() -> None:
    draft_kwargs = _mandate_draft(
        buyer_allowlist=["BUYER_B", "BUYER_A"]
    ).model_dump()
    mandate_a = InvestorMandate(id="MANDATE-2026-001", version=1, **draft_kwargs)
    reordered = dict(reversed(list(draft_kwargs.items())))
    mandate_b = InvestorMandate(id="MANDATE-2026-001", version=1, **reordered)

    assert mandate_a.canonical_message() == mandate_b.canonical_message()
    assert "buyerAllowlist: BUYER_A,BUYER_B" in mandate_a.canonical_message()


def test_canonical_message_excludes_signing_fields() -> None:
    mandate = _mandate(status=MandateStatus.ACTIVE)
    mandate = mandate.model_copy(
        update={"signature": "some-signature", "signed_at": "2026-08-02T00:00:00Z"}
    )
    message = mandate.canonical_message()

    assert "some-signature" not in message
    assert "signedAt" not in message
    assert "status" not in message
    assert message.startswith("InvoiceX Investment Mandate\nid: MANDATE-2026-001")


# ---------------------------------------------------------------------------
# ed25519 signature round trip through the service
# ---------------------------------------------------------------------------


def _service(tmp_path: Path) -> InvoiceService:
    settings = mock_settings(tmp_path / "uploads")
    return InvoiceService(
        settings=settings,
        agent_gateway=create_agent_gateway(settings),
        solana_gateway=create_solana_gateway(settings),
        storage=LocalDocumentStorage(settings),
    )


@pytest.mark.asyncio
async def test_activate_mandate_succeeds_with_a_real_wallet_signature(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    await service.initialize()
    keypair = Keypair()
    address = str(keypair.pubkey())

    preparation = await service.prepare_mandate(
        _mandate_draft(investor_wallet_address=address)
    )
    signature = str(keypair.sign_message(preparation.message.encode("utf-8")))

    activated = await service.activate_mandate(preparation.mandate.id, signature)

    assert activated.status == MandateStatus.ACTIVE
    assert activated.signature == signature
    assert activated.signed_at is not None
    assert service.get_mandate().id == preparation.mandate.id
    await service.close()


@pytest.mark.asyncio
async def test_activate_mandate_rejects_a_signature_from_a_different_wallet(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    await service.initialize()
    owner = Keypair()
    impostor = Keypair()

    preparation = await service.prepare_mandate(
        _mandate_draft(investor_wallet_address=str(owner.pubkey()))
    )
    wrong_signature = str(
        impostor.sign_message(preparation.message.encode("utf-8"))
    )

    with pytest.raises(StateConflictError):
        await service.activate_mandate(preparation.mandate.id, wrong_signature)
    with pytest.raises(NotFoundError):
        service.get_mandate()
    await service.close()


@pytest.mark.asyncio
async def test_activate_mandate_rejects_a_malformed_signature(tmp_path: Path) -> None:
    service = _service(tmp_path)
    await service.initialize()
    keypair = Keypair()
    preparation = await service.prepare_mandate(
        _mandate_draft(investor_wallet_address=str(keypair.pubkey()))
    )

    with pytest.raises(StateConflictError):
        await service.activate_mandate(preparation.mandate.id, "not-a-signature")
    await service.close()


# ---------------------------------------------------------------------------
# TreasuryMandatePolicy.rejection_reason — Mandate-aware branch (14 cases)
# ---------------------------------------------------------------------------


def test_mandate_aware_policy_accepts_a_consistent_baseline() -> None:
    policy = _policy()
    assert (
        policy.rejection_reason(_invoice(), mandate=_mandate(), today=TODAY) is None
    )


MANDATE_REJECTION_CASES = [
    (
        "no_risk_passport",
        {"risk_passport": None},
        {},
        {},
        "Risk Passport가 없습니다.",
    ),
    (
        "not_eligible",
        {
            "risk_passport": RiskPassport(
                invoice_id="INV-2026-001",
                eligibility=RiskEligibility.REVIEW_REQUIRED,
                risk_score=None,
                positive_factors=[],
                risk_factors=[],
                suggested_advance_rate_bps=None,
                suggested_advance_amount_usdc=None,
            )
        },
        {},
        {},
        "Risk Passport가 투자 적격 상태가 아닙니다.",
    ),
    (
        "emergency_stopped",
        {},
        {"status": MandateStatus.ACTIVE, "emergency_stopped": True},
        {},
        "투자자가 긴급 중지를 설정했습니다.",
    ),
    (
        "mandate_not_active",
        {},
        {"status": MandateStatus.DRAFT},
        {},
        "Mandate가 활성 상태가 아닙니다.",
    ),
    (
        "outside_validity_window",
        {},
        {"valid_from": "2026-01-01", "valid_until": "2026-06-01"},
        {},
        "Mandate 유효기간이 아닙니다.",
    ),
    (
        "risk_score_below_minimum",
        {},
        {"min_risk_score": 90},
        {},
        "Risk Score가 Mandate 최소 기준보다 낮습니다.",
    ),
    (
        "buyer_excluded",
        {},
        {"excluded_buyer_ids": ["BUYER_PRIME"]},
        {},
        "제외된 구매기업입니다.",
    ),
    (
        "buyer_not_in_allowlist",
        {},
        {"buyer_allowlist": ["OTHER_BUYER"]},
        {},
        "허용된 구매기업 목록에 없습니다.",
    ),
    (
        "advance_rate_exceeds_limit",
        {},
        {"max_advance_rate_bps": 5_000},
        {},
        "선지급률이 Mandate 한도를 초과합니다.",
    ),
    (
        "remaining_tenor_exceeds_limit",
        {},
        {"max_remaining_tenor_days": 10},
        {},
        "잔존 만기가 Mandate 허용 범위를 벗어납니다.",
    ),
    (
        "advance_amount_exceeds_per_invoice_limit",
        {},
        {"per_invoice_limit_usdc": 1_000},
        {},
        "조기정산금이 Mandate 건별 한도를 초과합니다.",
    ),
    (
        "outstanding_total_limit_exceeded",
        {},
        {"total_outstanding_limit_usdc": 20_000},
        {"outstanding_principal_usdc": 10_000},
        "총 미상환 투자잔액 한도를 초과합니다.",
    ),
    (
        "daily_new_investment_limit_exceeded",
        {},
        {"daily_new_investment_limit_usdc": 20_000},
        {"daily_invested_usdc": 10_000},
        "일일 신규 투자 한도를 초과합니다.",
    ),
    (
        "vault_balance_insufficient",
        {},
        {},
        {"available_vault_usdc": 10_000},
        "Agent Vault 잔액이 부족합니다.",
    ),
]


@pytest.mark.parametrize(
    "case_name,invoice_overrides,mandate_overrides,extra_kwargs,expected_message",
    MANDATE_REJECTION_CASES,
    ids=[case[0] for case in MANDATE_REJECTION_CASES],
)
def test_mandate_aware_policy_rejection_reasons(
    case_name: str,
    invoice_overrides: dict[str, object],
    mandate_overrides: dict[str, object],
    extra_kwargs: dict[str, object],
    expected_message: str,
) -> None:
    policy = _policy()
    invoice = _invoice(**invoice_overrides)
    mandate = _mandate(**mandate_overrides)

    reason = policy.rejection_reason(
        invoice,
        mandate=mandate,
        today=TODAY,
        **extra_kwargs,
    )

    assert reason == expected_message


def test_mandate_aware_policy_blocks_without_raising_on_unparseable_due_date() -> None:
    policy = _policy()
    invoice = _invoice(due_date="not-a-date")

    reason = policy.rejection_reason(invoice, mandate=_mandate(), today=TODAY)

    assert reason == "만기일 형식을 확인할 수 없습니다."


# ---------------------------------------------------------------------------
# mandate=None keeps the original settings-based guard unchanged
# ---------------------------------------------------------------------------


def test_no_mandate_falls_back_to_settings_based_policy_unchanged() -> None:
    policy = _policy(MANDATE_MIN_RISK_SCORE=80, MANDATE_MAX_ADVANCE_USDC=25_000)

    assert policy.rejection_reason(_invoice()) is None

    low_score = _invoice(
        risk_passport=RiskPassport(
            invoice_id="INV-2026-001",
            eligibility=RiskEligibility.ELIGIBLE,
            risk_score=70,
            positive_factors=[],
            risk_factors=[],
            suggested_advance_rate_bps=9_400,
            suggested_advance_amount_usdc=18_800,
        )
    )
    assert (
        policy.rejection_reason(low_score)
        == "Risk Score가 Mandate 최소 기준보다 낮습니다."
    )

    over_cap = _invoice(
        risk_passport=RiskPassport(
            invoice_id="INV-2026-001",
            eligibility=RiskEligibility.ELIGIBLE,
            risk_score=86,
            positive_factors=[],
            risk_factors=[],
            suggested_advance_rate_bps=9_400,
            suggested_advance_amount_usdc=30_000,
        )
    )
    assert (
        policy.rejection_reason(over_cap)
        == "조기정산금이 Mandate 건별 한도를 초과합니다."
    )


# ---------------------------------------------------------------------------
# Restart persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mandate_and_daily_invested_survive_an_api_restart(
    tmp_path: Path,
) -> None:
    settings = mock_settings(tmp_path / "uploads")
    client = FakeFirestoreClient()
    keypair = Keypair()
    address = str(keypair.pubkey())

    before_restart = _investor_service(settings, client)
    await before_restart.initialize()
    preparation = await before_restart.prepare_mandate(
        _mandate_draft(investor_wallet_address=address)
    )
    signature = str(keypair.sign_message(preparation.message.encode("utf-8")))
    activated = await before_restart.activate_mandate(
        preparation.mandate.id, signature
    )
    # Simulate a completed funding day without running the full invoice flow.
    before_restart._daily_invested_usdc["2026-08-02"] = 1_234
    await before_restart._persist(investor=True)
    await before_restart.close()

    after_restart = _investor_service(settings, client)
    await after_restart.initialize()
    dashboard = after_restart.investor_dashboard()

    assert dashboard.mandate is not None
    assert dashboard.mandate.id == activated.id
    assert dashboard.mandate.status == MandateStatus.ACTIVE
    assert dashboard.mandate.signature == signature
    assert after_restart._daily_invested_usdc.get("2026-08-02") == 1_234
    await after_restart.close()


# ---------------------------------------------------------------------------
# API contract: prepare -> activate -> GET, and emergency-stop
# ---------------------------------------------------------------------------


def test_mandate_api_prepare_activate_get_and_emergency_stop(
    client: TestClient,
) -> None:
    keypair = Keypair()
    address = str(keypair.pubkey())

    missing = client.get("/api/v1/investor/mandate")
    assert missing.status_code == 404

    draft_payload = {
        "investorWalletAddress": address,
        "totalOutstandingLimitUsdc": 100_000,
        "perInvoiceLimitUsdc": 20_000,
        "dailyNewInvestmentLimitUsdc": 50_000,
        "minRiskScore": 80,
        "maxRemainingTenorDays": 120,
        "maxAdvanceRateBps": 9_500,
        "minTargetNetYieldBps": 100,
        "validFrom": "2026-01-01",
        "validUntil": "2026-12-31",
    }
    prepared = client.post("/api/v1/investor/mandate/prepare", json=draft_payload)
    assert prepared.status_code == 200
    body = prepared.json()
    assert body["mandate"]["status"] == "DRAFT"
    mandate_id = body["mandate"]["id"]
    message = body["message"]

    signature = str(keypair.sign_message(message.encode("utf-8")))
    activated = client.post(
        "/api/v1/investor/mandate/activate",
        json={"mandateId": mandate_id, "signature": signature},
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "ACTIVE"

    fetched = client.get("/api/v1/investor/mandate")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == mandate_id

    dashboard = client.get("/api/v1/investor/dashboard").json()
    assert dashboard["mandate"]["id"] == mandate_id
    assert dashboard["mandateStatus"] == "ACTIVE"

    stopped = client.post(
        "/api/v1/investor/mandate/emergency-stop", json={"stopped": True}
    )
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "STOPPED"
    assert stopped.json()["emergencyStopped"] is True

    dashboard_after_stop = client.get("/api/v1/investor/dashboard").json()
    assert dashboard_after_stop["automatedInvestmentActive"] is False
    # STOPPED is mapped to the frontend's DRAFT literal (see investor_dashboard()).
    assert dashboard_after_stop["mandateStatus"] == "DRAFT"

    resumed = client.post(
        "/api/v1/investor/mandate/emergency-stop", json={"stopped": False}
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "ACTIVE"
    assert resumed.json()["emergencyStopped"] is False


def test_mandate_activate_with_wrong_wallet_signature_returns_409(
    client: TestClient,
) -> None:
    owner = Keypair()
    impostor = Keypair()
    draft_payload = {
        "investorWalletAddress": str(owner.pubkey()),
        "totalOutstandingLimitUsdc": 100_000,
        "perInvoiceLimitUsdc": 20_000,
        "dailyNewInvestmentLimitUsdc": 50_000,
        "minRiskScore": 80,
        "maxRemainingTenorDays": 120,
        "maxAdvanceRateBps": 9_500,
        "minTargetNetYieldBps": 100,
        "validFrom": "2026-01-01",
        "validUntil": "2026-12-31",
    }
    prepared = client.post(
        "/api/v1/investor/mandate/prepare", json=draft_payload
    ).json()
    wrong_signature = str(
        impostor.sign_message(prepared["message"].encode("utf-8"))
    )

    response = client.post(
        "/api/v1/investor/mandate/activate",
        json={"mandateId": prepared["mandate"]["id"], "signature": wrong_signature},
    )
    assert response.status_code == 409
