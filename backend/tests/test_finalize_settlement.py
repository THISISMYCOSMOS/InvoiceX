"""POST /settlement finishes an invoice the mock payment left unconfirmed."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from invoicex_backend.agents import MockAgentGateway
from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import StateConflictError
from invoicex_backend.models import (
    ChainTransfer,
    ChainTransferResult,
    InvoiceStatus,
    TransactionStatus,
)
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import MockSolanaGateway
from invoicex_backend.state_store import JsonStateStore
from invoicex_backend.storage import LocalDocumentStorage
from tests.conftest import mock_settings


class UnconfirmedFirstSolanaGateway(MockSolanaGateway):
    """Return PENDING for the first settlement, CONFIRMED afterwards."""

    def __init__(self, settings: BackendSettings) -> None:
        super().__init__(settings)
        self.settlement_calls = 0

    async def send_usdc(
        self,
        *,
        wallet_id: str,
        transfers: list[ChainTransfer],
        reference_id: str,
    ) -> ChainTransferResult:
        if not reference_id.startswith("settlement-"):
            return await super().send_usdc(
                wallet_id=wallet_id,
                transfers=transfers,
                reference_id=reference_id,
            )
        self.settlement_calls += 1
        if self.settlement_calls == 1:
            return ChainTransferResult(
                signature="PENDING_SIGNATURE",
                status=TransactionStatus.PENDING,
                from_address="DEMO_SETTLEMENT_PARTNER",
                provider="MOCK",
                sandbox=True,
            )
        return ChainTransferResult(
            signature="CONFIRMED_SIGNATURE",
            status=TransactionStatus.CONFIRMED,
            from_address="DEMO_SETTLEMENT_PARTNER",
            provider="MOCK",
            sandbox=True,
        )


def build_service(
    settings: BackendSettings,
    solana: MockSolanaGateway,
) -> InvoiceService:
    return InvoiceService(
        settings=settings,
        agent_gateway=MockAgentGateway(),
        solana_gateway=solana,
        storage=LocalDocumentStorage(settings),
        state_store=JsonStateStore(settings.resolved_state_file()),
    )


async def advance_to_funded(service: InvoiceService) -> str:
    seeded = await service.reset_demo()
    await service.analyze_seeded_documents(seeded.id)
    await service.complete_document_analysis(seeded.id)
    requested = await service.request_verification(seeded.id)
    assert requested.verification_id is not None
    await service.confirm_verification(requested.verification_id)
    await service.complete_risk_assessment(seeded.id)
    await service.respond_to_offer(seeded.id, "ACCEPT")
    await service.complete_funding(seeded.id)
    assert service.get_invoice(seeded.id).status is InvoiceStatus.FUNDED
    return seeded.id


def test_finalize_completes_an_unconfirmed_settlement(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    solana = UnconfirmedFirstSolanaGateway(settings)
    service = build_service(settings, solana)

    async def scenario() -> str:
        invoice_id = await advance_to_funded(service)
        stuck = await service.settle_mock_payment(invoice_id)
        # The chain did not confirm, so mock-payment cannot reach SETTLED.
        assert stuck.status is InvoiceStatus.SETTLING
        assert stuck.settlement is None

        finished = await service.finalize_settlement(invoice_id)
        assert finished.status is InvoiceStatus.SETTLED
        assert finished.settlement is not None
        assert finished.settlement.investor_settlement_usdc == 19_800
        assert finished.settlement_transaction is not None
        assert finished.settlement_transaction.signature == "CONFIRMED_SIGNATURE"
        return invoice_id

    invoice_id = asyncio.run(scenario())

    # And the completion is durable.
    assert build_service(settings, solana).get_invoice(invoice_id).status is (
        InvoiceStatus.SETTLED
    )


def test_finalize_is_idempotent_once_settled(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings, MockSolanaGateway(settings))

    async def scenario() -> None:
        invoice_id = await advance_to_funded(service)
        settled = await service.settle_mock_payment(invoice_id)
        assert settled.status is InvoiceStatus.SETTLED

        again = await service.finalize_settlement(invoice_id)
        assert again.status is InvoiceStatus.SETTLED
        assert again.settlement_transaction is not None
        assert settled.settlement_transaction is not None
        assert (
            again.settlement_transaction.signature
            == settled.settlement_transaction.signature
        )

    asyncio.run(scenario())


def test_finalize_rejects_an_invoice_that_never_settled(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings, MockSolanaGateway(settings))

    async def scenario() -> None:
        invoice_id = await advance_to_funded(service)
        with pytest.raises(StateConflictError, match="SETTLING"):
            await service.finalize_settlement(invoice_id)

    asyncio.run(scenario())


def test_mock_payment_still_reaches_settled_in_one_call(tmp_path: Path) -> None:
    """httpAdapter relies on mock-payment alone completing the settlement."""

    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings, MockSolanaGateway(settings))

    async def scenario() -> None:
        invoice_id = await advance_to_funded(service)
        settled = await service.settle_mock_payment(invoice_id)
        assert settled.status is InvoiceStatus.SETTLED
        assert settled.settlement is not None

    asyncio.run(scenario())
