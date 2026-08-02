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
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import IntegrationError
from invoicex_backend.models import ChainTransfer, TransactionStatus
from invoicex_backend.solana import MockSolanaGateway, PrivySolanaGateway
from tests.conftest import mock_settings

RWA_PRIVY_SETTINGS: dict[str, object] = {
    "_env_file": None,
    "AGENT_MODE": "mock",
    "SOLANA_MODE": "privy",
    "PRIVY_APP_ID": "app-id",
    "PRIVY_APP_SECRET": "app-secret",
    "PRIVY_TREASURY_WALLET_ID": "treasury",
    "PRIVY_RWA_WALLET_ID": "rwa-wallet",
    "PRIVY_SPONSOR_WALLET_ID": "sponsor-wallet",
    "PRIVY_API_BASE_URL": "https://privy.test",
    "SOLANA_RPC_URL": "https://rpc.test",
}


def _wallet_id_from_path(path: str) -> str:
    # /v1/wallets/{wallet_id} or /v1/wallets/{wallet_id}/rpc
    return path.split("/")[3]


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
    submitted_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else {}
        if request.url.host == "privy.test" and request.method == "GET":
            return httpx.Response(
                200,
                json={"chain_type": "solana", "address": owner},
            )
        if request.url.host == "privy.test":
            submitted.update(payload)
            submitted_headers.update(request.headers)
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
    assert submitted["caip2"] == settings.solana_caip2
    assert submitted["reference_id"] == "settlement-INV-2026-001"
    assert submitted_headers["privy-idempotency-key"] == (
        "invoicex:settlement-INV-2026-001"
    )
    encoded = submitted["params"]["transaction"]  # type: ignore[index]
    transaction = VersionedTransaction.from_bytes(base64.b64decode(encoded))
    assert len(transaction.message.instructions) == 4


@pytest.mark.asyncio
async def test_privy_gateway_wraps_network_failures(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="mock",
        SOLANA_MODE="privy",
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_TREASURY_WALLET_ID="treasury",
        PRIVY_API_BASE_URL="https://privy.test",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)

    with pytest.raises(IntegrationError, match="network request failed"):
        await gateway.send_usdc(
            wallet_id="treasury",
            transfers=[
                ChainTransfer(
                    to_address=str(Pubkey.new_unique()),
                    amount_usdc=1,
                )
            ],
            reference_id="funding-INV-2026-001",
        )
    await client.aclose()


@pytest.mark.asyncio
async def test_privy_gateway_verifies_investor_usdc_deposit(tmp_path: Path) -> None:
    investor = str(Pubkey.new_unique())
    treasury = str(Pubkey.new_unique())
    signature = str(Signature.default())

    def token_balance(owner: str, amount: int, mint: str) -> dict[str, object]:
        return {
            "mint": mint,
            "owner": owner,
            "uiTokenAmount": {"amount": str(amount), "decimals": 6},
        }

    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="mock",
        SOLANA_MODE="privy",
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_TREASURY_WALLET_ID="treasury",
        PRIVY_API_BASE_URL="https://privy.test",
        SOLANA_RPC_URL="https://rpc.test",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["method"] == "getSignatureStatuses":
            result: object = {
                "value": [{"err": None, "confirmationStatus": "confirmed"}]
            }
        else:
            result = {
                "meta": {
                    "err": None,
                    "preTokenBalances": [
                        token_balance(investor, 20_000_000, settings.solana_usdc_mint),
                        token_balance(treasury, 0, settings.solana_usdc_mint),
                    ],
                    "postTokenBalances": [
                        token_balance(investor, 0, settings.solana_usdc_mint),
                        token_balance(treasury, 20_000_000, settings.solana_usdc_mint),
                    ],
                },
                "transaction": {
                    "message": {
                        "accountKeys": [
                            {"pubkey": investor, "signer": True, "writable": True},
                            {"pubkey": treasury, "signer": False, "writable": True},
                        ]
                    }
                },
            }
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "result": result, "id": 1},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)

    status = await gateway.verify_usdc_deposit(
        signature=signature,
        from_address=investor,
        to_address=treasury,
        amount_usdc=20,
    )
    assert status is TransactionStatus.CONFIRMED

    with pytest.raises(IntegrationError, match="did not match preparation"):
        await gateway.verify_usdc_deposit(
            signature=signature,
            from_address=investor,
            to_address=treasury,
            amount_usdc=19,
        )
    await client.aclose()


@pytest.mark.asyncio
async def test_privy_gateway_issues_rwa_signed_by_rwa_then_sponsor_wallet(
    tmp_path: Path,
) -> None:
    sponsor = Pubkey.new_unique()
    rwa = Pubkey.new_unique()
    invoice_id = "INV-2026-001"
    mint = Pubkey.create_with_seed(sponsor, invoice_id, TOKEN_PROGRAM_ID)
    escrow_ata = get_associated_token_address(rwa, mint, TOKEN_PROGRAM_ID)
    wallet_addresses = {"sponsor-wallet": str(sponsor), "rwa-wallet": str(rwa)}
    signed_by_rwa = "signed-by-rwa-base64"
    signed_by_sponsor = "signed-by-sponsor-base64"
    final_signature = str(Signature.from_bytes(bytes(range(1, 65))))
    sign_calls: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "privy.test":
            wallet_id = _wallet_id_from_path(request.url.path)
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "chain_type": "solana",
                        "address": wallet_addresses[wallet_id],
                    },
                )
            payload = json.loads(request.content)
            assert payload["method"] == "signTransaction"
            sign_calls.append(
                {
                    "wallet_id": wallet_id,
                    "transaction": payload["params"]["transaction"],
                }
            )
            signed = signed_by_rwa if wallet_id == "rwa-wallet" else signed_by_sponsor
            return httpx.Response(
                200,
                json={
                    "method": "signTransaction",
                    "data": {"signed_transaction": signed, "encoding": "base64"},
                },
            )
        payload = json.loads(request.content)
        method = payload["method"]
        if method == "getAccountInfo":
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": 1, "result": {"context": {}, "value": None}},
            )
        if method == "getMinimumBalanceForRentExemption":
            return httpx.Response(
                200, json={"jsonrpc": "2.0", "id": 1, "result": 1_461_600}
            )
        if method == "getLatestBlockhash":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"value": {"blockhash": str(Hash.default())}},
                },
            )
        if method == "sendTransaction":
            return httpx.Response(
                200, json={"jsonrpc": "2.0", "id": 1, "result": final_signature}
            )
        if method == "getSignatureStatuses":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "value": [{"err": None, "confirmationStatus": "confirmed"}]
                    },
                },
            )
        raise AssertionError(f"unexpected Solana RPC method {method}")

    settings = BackendSettings(
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        **RWA_PRIVY_SETTINGS,
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)

    issuance = await gateway.issue_invoice_rwa(invoice_id=invoice_id)
    await client.aclose()

    assert issuance.mint_address == str(mint)
    assert issuance.escrow_address == str(rwa)
    assert issuance.escrow_token_account == str(escrow_ata)
    assert issuance.already_issued is False
    assert issuance.signature == final_signature
    assert issuance.status is TransactionStatus.CONFIRMED
    assert issuance.provider == "PRIVY"
    assert issuance.sandbox is False

    assert [call["wallet_id"] for call in sign_calls] == ["rwa-wallet", "sponsor-wallet"]
    # The Sponsor's signing request must carry forward the RWA wallet's
    # already-signed transaction (cumulative signing), not a fresh one.
    assert sign_calls[1]["transaction"] == signed_by_rwa

    unsigned = VersionedTransaction.from_bytes(
        base64.b64decode(sign_calls[0]["transaction"])
    )
    assert len(unsigned.message.instructions) == 5
    assert unsigned.message.header.num_required_signatures == 2


@pytest.mark.asyncio
async def test_privy_gateway_skips_reissuing_an_existing_rwa_mint(
    tmp_path: Path,
) -> None:
    sponsor = Pubkey.new_unique()
    rwa = Pubkey.new_unique()
    invoice_id = "INV-2026-002"
    mint = Pubkey.create_with_seed(sponsor, invoice_id, TOKEN_PROGRAM_ID)
    wallet_addresses = {"sponsor-wallet": str(sponsor), "rwa-wallet": str(rwa)}
    sign_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "privy.test":
            wallet_id = _wallet_id_from_path(request.url.path)
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "chain_type": "solana",
                        "address": wallet_addresses[wallet_id],
                    },
                )
            sign_calls.append(wallet_id)
            return httpx.Response(
                200,
                json={
                    "method": "signTransaction",
                    "data": {"signed_transaction": "unused", "encoding": "base64"},
                },
            )
        payload = json.loads(request.content)
        assert payload["method"] == "getAccountInfo"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "context": {},
                    "value": {
                        "data": ["", "base64"],
                        "executable": False,
                        "lamports": 1_461_600,
                        "owner": str(TOKEN_PROGRAM_ID),
                        "rentEpoch": 0,
                    },
                },
            },
        )

    settings = BackendSettings(
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        **RWA_PRIVY_SETTINGS,
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)

    issuance = await gateway.issue_invoice_rwa(invoice_id=invoice_id)
    await client.aclose()

    assert issuance.already_issued is True
    assert issuance.mint_address == str(mint)
    assert issuance.signature is None
    assert issuance.status is TransactionStatus.CONFIRMED
    assert sign_calls == []


@pytest.mark.asyncio
async def test_privy_gateway_derives_deterministic_mint_addresses_per_invoice(
    tmp_path: Path,
) -> None:
    sponsor = Pubkey.new_unique()
    rwa = Pubkey.new_unique()
    wallet_addresses = {"sponsor-wallet": str(sponsor), "rwa-wallet": str(rwa)}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "privy.test":
            wallet_id = _wallet_id_from_path(request.url.path)
            return httpx.Response(
                200,
                json={"chain_type": "solana", "address": wallet_addresses[wallet_id]},
            )
        payload = json.loads(request.content)
        assert payload["method"] == "getAccountInfo"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"context": {}, "value": {"lamports": 1}},
            },
        )

    settings = BackendSettings(
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        **RWA_PRIVY_SETTINGS,
    )

    async def issue(invoice_id: str) -> str:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gateway = PrivySolanaGateway(settings, http_client=client)
        result = await gateway.issue_invoice_rwa(invoice_id=invoice_id)
        await client.aclose()
        return result.mint_address

    first = await issue("INV-2026-101")
    repeat = await issue("INV-2026-101")
    second = await issue("INV-2026-102")

    assert first == repeat
    assert first != second
    assert first == str(Pubkey.create_with_seed(sponsor, "INV-2026-101", TOKEN_PROGRAM_ID))


@pytest.mark.asyncio
async def test_privy_gateway_rejects_invoice_ids_longer_than_32_bytes(
    tmp_path: Path,
) -> None:
    settings = BackendSettings(
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        **RWA_PRIVY_SETTINGS,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"no network call expected, got {request.url}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)

    with pytest.raises(IntegrationError, match="32바이트"):
        await gateway.issue_invoice_rwa(invoice_id="INV-2026-" + "9" * 40)
    await client.aclose()


@pytest.mark.asyncio
async def test_mock_rwa_issuance_is_deterministic_and_idempotent(
    tmp_path: Path,
) -> None:
    settings = mock_settings(tmp_path / "uploads")
    gateway = MockSolanaGateway(settings)

    calls = [gateway.issue_invoice_rwa(invoice_id="INV-2026-001") for _ in range(50)]
    results = await asyncio.gather(*calls)
    assert len({result.mint_address for result in results}) == 1
    assert len({result.escrow_token_account for result in results}) == 1
    assert len({result.signature for result in results}) == 1
    assert any(not result.already_issued for result in results)
    assert any(result.already_issued for result in results)
    assert all(result.status is TransactionStatus.CONFIRMED for result in results)
    assert all(result.provider == "MOCK" and result.sandbox for result in results)

    other = await gateway.issue_invoice_rwa(invoice_id="INV-2026-002")
    assert other.mint_address != results[0].mint_address
    assert other.escrow_address == results[0].escrow_address
