from __future__ import annotations

from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient

from invoicex_backend.agents import create_agent_gateway
from invoicex_backend.app import create_app, create_document_storage, create_repository
from invoicex_backend.errors import IntegrationError
from invoicex_backend.models import BlockchainTransaction, InvoiceStatus, RwaAsset, TransactionStatus
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import MockSolanaGateway
from tests.conftest import mock_settings


BUYER_WALLET = "DemoBuyerEmbeddedWallet"
INVESTOR_WALLET = "DemoInvestorEmbeddedWallet"


class RecordingPaymentGateway(MockSolanaGateway):
    def __init__(self, settings) -> None:
        super().__init__(settings)
        self.send_counts: Counter[str] = Counter()
        self.fail_platform_fee_once = True

    async def verify_usdc_payment(
        self,
        *,
        signature: str,
        sender_wallet_address: str,
        recipient_wallet_address: str,
        amount_base_units: int,
    ) -> bool:
        return (
            signature == "valid-payment-signature"
            and sender_wallet_address == BUYER_WALLET
            and recipient_wallet_address == await self.settlement_wallet_address()
            and amount_base_units == 10_000_000_000
        )

    async def send_usdc(self, *, wallet_id, transfers, reference_id):
        self.send_counts[reference_id] += 1
        if reference_id.startswith("platform-fee-") and self.fail_platform_fee_once:
            self.fail_platform_fee_once = False
            raise IntegrationError("temporary platform fee payout failure")
        return await super().send_usdc(
            wallet_id=wallet_id,
            transfers=transfers,
            reference_id=reference_id,
        )


class DirectBuyerPaymentGateway(RecordingPaymentGateway):
    mode = "direct"

    async def verify_usdc_payment(
        self,
        *,
        signature: str,
        sender_wallet_address: str,
        recipient_wallet_address: str,
        amount_base_units: int,
    ) -> bool:
        return signature == "direct-payment-signature" and sender_wallet_address == BUYER_WALLET and (
            (recipient_wallet_address == INVESTOR_WALLET and amount_base_units == 9_900_000_000)
            or (recipient_wallet_address == self._settings.platform_fee_wallet_address and amount_base_units == 100_000_000)
        )


def _funded_invoice(client: TestClient, service: InvoiceService, contract_files) -> str:
    invoice_id = client.post("/api/v1/invoices", files=contract_files).json()["invoice"]["id"]
    verification = client.post(f"/api/v1/invoices/{invoice_id}/verification-request").json()["invoice"]
    client.post(f"/api/v1/verifications/{verification['verificationId']}/confirm")

    invoice = service._invoice(invoice_id)
    assert invoice.risk_passport is not None
    source_passport = invoice.risk_passport
    if source_passport.early_settlement_terms is None:
        source_passport = next(
            candidate.risk_passport
            for candidate in service._invoices.values()
            if candidate.id != invoice_id
            and candidate.risk_passport is not None
            and candidate.risk_passport.early_settlement_terms is not None
        )
    assert source_passport.early_settlement_terms is not None
    terms = source_passport.early_settlement_terms.model_copy(
        update={
            "face_value_usdc": 10_000,
            "face_value_base_units": "10000000000",
            "purchase_amount_usdc": 8_900,
            "purchase_amount_base_units": "8900000000",
            "platform_fee_usdc": 100,
            "platform_fee_base_units": "100000000",
            "supplier_expected_settlement_usdc": 8_900,
            "supplier_settlement_base_units": "8900000000",
            "expected_investor_return_usdc": 1_000,
            "investor_net_return_base_units": "1000000000",
            "investor_settlement_usdc": 9_900,
            "investor_settlement_base_units": "9900000000",
        }
    )
    invoice.risk_passport = source_passport.model_copy(
        update={
            "invoice_id": invoice.id,
            "invoice_face_value_usdc": 10_000,
            "invoice_face_value_base_units": "10000000000",
            "early_settlement_terms": terms,
        }
    )
    invoice.buyer.wallet_address = BUYER_WALLET
    invoice.rwa_asset = RwaAsset(
        invoice_id=invoice.id,
        mint_address="DEMO_RWA_MINT",
        escrow_token_account="DEMO_RWA_ESCROW",
        status="SOLD",
        issue_transaction=BlockchainTransaction(
            signature="demo-rwa-issue-signature",
            status=TransactionStatus.CONFIRMED,
            amount_usdc=0,
            amount_base_units="0",
            from_address="DEMO_PLATFORM",
            to_address="DEMO_RWA_ESCROW",
            explorer_url="https://explorer.solana.com",
            created_at="2026-01-01T00:00:00+00:00",
            sandbox=True,
            provider="MOCK",
        ),
        owner_vault_address="DEMO_AGENT_VAULT",
        owner_wallet_address=INVESTOR_WALLET,
        face_value_usdc=10_000,
        face_value_base_units="10000000000",
        issuance_price_usdc=8_900,
        issuance_price_base_units="8900000000",
        purchase_price_usdc=8_900,
        purchase_price_base_units="8900000000",
    )
    service._repository.save_rwa_asset(invoice.rwa_asset)
    invoice.status = InvoiceStatus.FUNDED
    service._save_invoice(invoice)
    return invoice_id


def test_buyer_payment_validation_and_idempotent_partial_settlement(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    settings = mock_settings(tmp_path / "uploads")
    gateway = RecordingPaymentGateway(settings)
    service = InvoiceService(
        settings=settings,
        agent_gateway=create_agent_gateway(settings),
        solana_gateway=gateway,
        storage=create_document_storage(settings),
        repository=create_repository(settings),
    )
    with TestClient(create_app(settings=settings, service=service)) as client:
        invoice_id = _funded_invoice(client, service, contract_files)
        preparation = client.get(f"/api/v1/invoices/{invoice_id}/buyer-payment/prepare")
        assert preparation.status_code == 200
        assert preparation.json()["buyerWalletAddress"] == BUYER_WALLET
        assert preparation.json()["amountUsdc"] == 10_000
        assert preparation.json()["amountBaseUnits"] == "10000000000"

        for invalid_signature in ("wrong-amount-signature-0001", "wrong-wallet-signature-0001"):
            rejected = client.post(
                f"/api/v1/invoices/{invoice_id}/buyer-payment/confirm",
                json={"signature": invalid_signature},
            )
            assert rejected.status_code == 409

        partial = client.post(
            f"/api/v1/invoices/{invoice_id}/buyer-payment/confirm",
            json={"signature": "valid-payment-signature"},
        )
        assert partial.status_code == 502
        failed = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert failed["status"] == "SETTLEMENT_FAILED"
        assert failed["buyerPaymentTransaction"]["signature"] == "valid-payment-signature"
        assert failed["investorPayoutTransaction"] is not None
        assert failed["investorPayoutTransaction"]["toAddress"] == INVESTOR_WALLET
        assert failed["platformFeeTransaction"] is None

        retried = client.post(
            f"/api/v1/invoices/{invoice_id}/buyer-payment/confirm",
            json={"signature": "valid-payment-signature"},
        )
        assert retried.status_code == 200
        settled = retried.json()["invoice"]
        assert settled["status"] == "SETTLED"
        assert settled["rwaAsset"] is None or settled["rwaAsset"]["status"] == "SETTLED"
        assert gateway.send_counts[f"investor-payout-{invoice_id}"] == 1
        assert gateway.send_counts[f"platform-fee-{invoice_id}"] == 2

        duplicate = client.post(
            f"/api/v1/invoices/{invoice_id}/buyer-payment/confirm",
            json={"signature": "valid-payment-signature"},
        )
        assert duplicate.status_code == 200
        assert gateway.send_counts[f"investor-payout-{invoice_id}"] == 1

        different_signature = client.post(
            f"/api/v1/invoices/{invoice_id}/buyer-payment/confirm",
            json={"signature": "different-payment-signature-0001"},
        )
        assert different_signature.status_code == 409

        second_invoice_id = _funded_invoice(client, service, contract_files)
        reused = client.post(
            f"/api/v1/invoices/{second_invoice_id}/buyer-payment/confirm",
            json={"signature": "valid-payment-signature"},
        )
        assert reused.status_code == 409


def test_direct_buyer_payment_sends_proceeds_to_the_rwa_owner_wallet(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    settings = mock_settings(tmp_path / "uploads")
    gateway = DirectBuyerPaymentGateway(settings)
    service = InvoiceService(
        settings=settings,
        agent_gateway=create_agent_gateway(settings),
        solana_gateway=gateway,
        storage=create_document_storage(settings),
        repository=create_repository(settings),
    )
    with TestClient(create_app(settings=settings, service=service)) as client:
        invoice_id = _funded_invoice(client, service, contract_files)
        preparation = client.get(f"/api/v1/invoices/{invoice_id}/buyer-payment/prepare")
        assert preparation.status_code == 200
        assert preparation.json()["transfers"] == [
            {
                "recipientWalletAddress": INVESTOR_WALLET,
                "amountUsdc": 9_900,
                    "amountBaseUnits": "9900000000",
            },
            {
                "recipientWalletAddress": settings.platform_fee_wallet_address,
                "amountUsdc": 100,
                    "amountBaseUnits": "100000000",
            },
        ]

        settled = client.post(
            f"/api/v1/invoices/{invoice_id}/buyer-payment/confirm",
            json={"signature": "direct-payment-signature"},
        )
        assert settled.status_code == 200
        invoice = settled.json()["invoice"]
        assert invoice["status"] == "SETTLED"
        assert invoice["investorPayoutTransaction"]["toAddress"] == INVESTOR_WALLET
        assert invoice["platformFeeTransaction"]["toAddress"] == settings.platform_fee_wallet_address
        assert gateway.send_counts == Counter()
