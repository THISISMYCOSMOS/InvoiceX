from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

import httpx
import pytest
from solders.hash import Hash
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import ChainTransfer, TransactionStatus
from invoicex_backend.solana import MockSolanaGateway, PrivySolanaGateway
from tests.conftest import mock_settings


@pytest.mark.asyncio
async def test_mock_solana_is_concurrency_safe_and_idempotent(
    tmp_path: Path,
) -> None:
    settings = mock_settings(tmp_path / "uploads")
    gateway = MockSolanaGateway(settings)
    calls = [
        gateway.send_usdc(
            wallet_id="wallet",
            transfers=[ChainTransfer(to_address="destination", amount_usdc=18_800)],
            reference_id="funding-INV-001",
        )
        for _ in range(100)
    ]
    results = await asyncio.gather(*calls)
    assert len({result.signature for result in results}) == 1
    assert all(result.status is TransactionStatus.CONFIRMED for result in results)


@pytest.mark.asyncio
async def test_privy_gateway_builds_and_submits_spl_transaction(
    tmp_path: Path,
) -> None:
    owner = str(Pubkey.new_unique())
    investor = str(Pubkey.new_unique())
    platform = str(Pubkey.new_unique())
    supplier = str(Pubkey.new_unique())
    signature = str(Signature.from_bytes(bytes(range(64))))
    submitted: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else {}
        if request.url.host == "privy.test" and request.method == "GET":
            return httpx.Response(
                200,
                json={"chain_type": "solana", "address": owner},
            )
        if request.url.host == "privy.test":
            submitted.update(payload)
            submitted["idempotency_key"] = request.headers.get(
                "privy-idempotency-key"
            )
            return httpx.Response(200, json={"data": {"hash": signature}})
        if payload["method"] == "getLatestBlockhash":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": {"value": {"blockhash": str(Hash.default())}},
                    "id": 1,
                },
            )
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "result": {
                    "value": [
                        {
                            "err": None,
                            "confirmationStatus": "confirmed",
                        }
                    ]
                },
                "id": 1,
            },
        )

    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="mock",
        SOLANA_MODE="privy",
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_TREASURY_WALLET_ID="treasury",
        PRIVY_SETTLEMENT_WALLET_ID="settlement",
        PRIVY_API_BASE_URL="https://privy.test",
        SOLANA_RPC_URL="https://rpc.test",
        SUPPLIER_WALLET_ADDRESS=supplier,
        INVESTOR_SETTLEMENT_WALLET_ADDRESS=investor,
        PLATFORM_FEE_WALLET_ADDRESS=platform,
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)
    result = await gateway.send_usdc(
        wallet_id="settlement",
        transfers=[
            ChainTransfer(to_address=investor, amount_usdc=19_800),
            ChainTransfer(to_address=platform, amount_usdc=200),
        ],
        reference_id="settlement-INV-2026-001",
    )
    await client.aclose()

    assert result.signature == signature
    assert result.status is TransactionStatus.CONFIRMED
    assert submitted["method"] == "signAndSendTransaction"
    assert submitted["caip2"] == settings.resolved_caip2()
    assert submitted["reference_id"] == "settlement-INV-2026-001"
    assert submitted["idempotency_key"] == "invoicex:settlement-INV-2026-001"
    encoded = submitted["params"]["transaction"]  # type: ignore[index]
    transaction = VersionedTransaction.from_bytes(base64.b64decode(encoded))
    assert len(transaction.message.instructions) == 4
