from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

import httpx
import pytest
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import to_bytes_versioned
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import ChainTransfer, TransactionStatus
from invoicex_backend.solana import (
    DirectSolanaGateway,
    MockSolanaGateway,
    PrivySolanaGateway,
)
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
        PRIVY_RWA_ISSUER_WALLET_ID="issuer",
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
    encoded = submitted["params"]["transaction"]  # type: ignore[index]
    transaction = VersionedTransaction.from_bytes(base64.b64decode(encoded))
    assert len(transaction.message.instructions) == 4


@pytest.mark.asyncio
async def test_privy_gateway_sponsors_an_externally_signed_vault_deposit(
    tmp_path: Path,
) -> None:
    investor = Keypair()
    treasury = str(Pubkey.new_unique())
    sponsor = str(Pubkey.new_unique())
    signature = str(Signature.from_bytes(bytes(range(64))))
    submitted: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else {}
        if request.url.host == "privy.test" and request.method == "GET":
            address = sponsor if request.url.path.endswith("/sponsor") else treasury
            return httpx.Response(200, json={"chain_type": "solana", "address": address})
        if request.url.host == "privy.test":
            submitted.update(payload)
            return httpx.Response(200, json={"data": {"hash": signature}})
        if payload["method"] == "getLatestBlockhash":
            result: object = {"value": {"blockhash": str(Hash.default())}}
        elif payload["method"] == "getSignatureStatuses":
            result = {"value": [{"err": None, "confirmationStatus": "confirmed"}]}
        else:
            raise AssertionError(f"unexpected RPC method: {payload['method']}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "result": result, "id": 1})

    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="mock",
        SOLANA_MODE="privy",
        GASLESS_ENABLED=True,
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_TREASURY_WALLET_ID="treasury",
        PRIVY_RWA_ISSUER_WALLET_ID="issuer",
        PRIVY_TREASURY_WALLET_ADDRESS=treasury,
        PRIVY_SPONSOR_WALLET_ID="sponsor",
        PRIVY_SPONSOR_WALLET_ADDRESS=sponsor,
        PRIVY_API_BASE_URL="https://privy.test",
        SOLANA_RPC_URL="https://rpc.test",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)
    prepared = await gateway.prepare_vault_deposit(
        owner_wallet_address=str(investor.pubkey()),
        amount_usdc=1,
    )
    unsigned = VersionedTransaction.from_bytes(base64.b64decode(prepared.transaction_base64))
    signatures = list(unsigned.signatures)
    investor_index = list(unsigned.message.account_keys).index(investor.pubkey())
    signatures[investor_index] = investor.sign_message(to_bytes_versioned(unsigned.message))
    transaction = VersionedTransaction.populate(unsigned.message, signatures)
    result = await gateway.sponsor_vault_deposit(
        owner_wallet_address=str(investor.pubkey()),
        amount_usdc=1,
        prepared_transaction_base64=prepared.transaction_base64,
        signed_transaction_base64=base64.b64encode(bytes(transaction)).decode("ascii"),
        reference_id="gasless-deposit-test",
    )
    await client.aclose()

    assert prepared.sponsored is True
    assert prepared.sponsor_wallet_address == sponsor
    assert str(transaction.message.account_keys[0]) == sponsor
    assert result.signature == signature
    assert submitted["method"] == "signAndSendTransaction"
    assert submitted["reference_id"] == "gasless-deposit-test"


@pytest.mark.asyncio
async def test_privy_gateway_issues_and_atomically_exchanges_rwa(
    tmp_path: Path,
) -> None:
    treasury = str(Pubkey.new_unique())
    issuer = str(Pubkey.new_unique())
    sponsor = str(Pubkey.new_unique())
    supplier = str(Pubkey.new_unique())
    signature = str(Signature.from_bytes(bytes(reversed(range(64)))))
    methods: list[tuple[str, str]] = []
    submitted_transactions: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else {}
        if request.url.host == "privy.test" and request.method == "GET":
            address = {
                "/v1/wallets/issuer": issuer,
                "/v1/wallets/sponsor": sponsor,
            }.get(request.url.path, treasury)
            return httpx.Response(200, json={"chain_type": "solana", "address": address})
        if request.url.host == "privy.test":
            method = payload["method"]
            methods.append((request.url.path, method))
            submitted_transactions.append((request.url.path, payload["params"]["transaction"]))
            if method == "signTransaction":
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "encoding": "base64",
                            "signed_transaction": payload["params"]["transaction"],
                        }
                    },
                )
            return httpx.Response(200, json={"data": {"hash": signature}})
        if payload["method"] == "getMinimumBalanceForRentExemption":
            result: object = 1_000_000
        elif payload["method"] == "getLatestBlockhash":
            result = {"value": {"blockhash": str(Hash.default())}}
        elif payload["method"] == "getSignatureStatuses":
            result = {"value": [{"err": None, "confirmationStatus": "confirmed"}]}
        else:
            raise AssertionError(f"unexpected RPC method: {payload['method']}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "result": result, "id": 1})

    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="mock",
        SOLANA_MODE="privy",
        GASLESS_ENABLED=True,
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_TREASURY_WALLET_ID="treasury",
        PRIVY_RWA_ISSUER_WALLET_ID="issuer",
        PRIVY_TREASURY_WALLET_ADDRESS=treasury,
        PRIVY_SPONSOR_WALLET_ID="sponsor",
        PRIVY_SPONSOR_WALLET_ADDRESS=sponsor,
        PRIVY_API_BASE_URL="https://privy.test",
        SOLANA_RPC_URL="https://rpc.test",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)
    issued = await gateway.issue_rwa(invoice_id="INV-2026-001")
    purchase = await gateway.purchase_rwa(
        invoice_id="INV-2026-001",
        rwa_mint_address=issued.mint_address,
        escrow_token_account=issued.escrow_token_account,
        supplier_wallet_address=supplier,
        amount_usdc=1,
    )
    await client.aclose()

    assert issued.transaction.provider == "PRIVY"
    assert purchase.provider == "PRIVY"
    assert methods == [
        ("/v1/wallets/issuer/rpc", "signTransaction"),
        ("/v1/wallets/sponsor/rpc", "signAndSendTransaction"),
        ("/v1/wallets/issuer/rpc", "signTransaction"),
        ("/v1/wallets/treasury/rpc", "signTransaction"),
        ("/v1/wallets/sponsor/rpc", "signAndSendTransaction"),
    ]
    submitted_by_sponsor = [
        encoded
        for path, encoded in submitted_transactions
        if path == "/v1/wallets/sponsor/rpc"
    ]
    assert len(submitted_by_sponsor) == 2
    for encoded in submitted_by_sponsor:
        transaction = VersionedTransaction.from_bytes(base64.b64decode(encoded))
        assert str(transaction.message.account_keys[0]) == sponsor
    assert issued.transaction.from_address == issuer
    assert purchase.from_address == treasury


@pytest.mark.asyncio
async def test_privy_gateway_funds_development_wallet_with_sponsor(
    tmp_path: Path,
) -> None:
    treasury = str(Pubkey.new_unique())
    sponsor = str(Pubkey.new_unique())
    recipient = str(Pubkey.new_unique())
    signature = str(Signature.from_bytes(bytes(range(64))))
    methods: list[tuple[str, str]] = []
    submitted: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else {}
        if request.url.host == "privy.test" and request.method == "GET":
            address = sponsor if request.url.path.endswith("/sponsor") else treasury
            return httpx.Response(200, json={"chain_type": "solana", "address": address})
        if request.url.host == "privy.test":
            method = payload["method"]
            methods.append((request.url.path, method))
            submitted.append((request.url.path, payload["params"]["transaction"]))
            if method == "signTransaction":
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "encoding": "base64",
                            "signed_transaction": payload["params"]["transaction"],
                        }
                    },
                )
            return httpx.Response(200, json={"data": {"hash": signature}})
        if payload["method"] == "getLatestBlockhash":
            result: object = {"value": {"blockhash": str(Hash.default())}}
        elif payload["method"] == "getSignatureStatuses":
            result = {"value": [{"err": None, "confirmationStatus": "confirmed"}]}
        else:
            raise AssertionError(f"unexpected RPC method: {payload['method']}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "result": result, "id": 1})

    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="mock",
        SOLANA_MODE="privy",
        GASLESS_ENABLED=True,
        SOLANA_DEMO_TRANSFER_AMOUNT_USDC=1,
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_TREASURY_WALLET_ID="treasury",
        PRIVY_TREASURY_WALLET_ADDRESS=treasury,
        PRIVY_RWA_ISSUER_WALLET_ID="issuer",
        PRIVY_SPONSOR_WALLET_ID="sponsor",
        PRIVY_SPONSOR_WALLET_ADDRESS=sponsor,
        PRIVY_API_BASE_URL="https://privy.test",
        SOLANA_RPC_URL="https://rpc.test",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = PrivySolanaGateway(settings, http_client=client)
    result = await gateway.fund_development_wallet(
        recipient_wallet_address=recipient,
        amount_usdc=1,
        reference_id="devnet-fund-test",
    )
    await client.aclose()

    assert result.provider == "PRIVY"
    assert result.from_address == treasury
    assert methods == [
        ("/v1/wallets/treasury/rpc", "signTransaction"),
        ("/v1/wallets/sponsor/rpc", "signAndSendTransaction"),
    ]
    sponsor_transaction = VersionedTransaction.from_bytes(
        base64.b64decode(submitted[-1][1])
    )
    assert str(sponsor_transaction.message.account_keys[0]) == sponsor
    assert treasury in {str(key) for key in sponsor_transaction.message.account_keys}
    assert recipient in {str(key) for key in sponsor_transaction.message.account_keys}


@pytest.mark.asyncio
async def test_direct_gateway_issues_and_atomically_purchases_rwa(
    tmp_path: Path,
) -> None:
    platform = Keypair()
    vault = Keypair()
    stablecoin_mint = Pubkey.new_unique()
    supplier = Pubkey.new_unique()
    signatures: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload["method"]
        if method == "getMinimumBalanceForRentExemption":
            result: object = 1_000_000
        elif method == "getLatestBlockhash":
            result = {"value": {"blockhash": str(Hash.default())}}
        elif method == "sendTransaction":
            transaction = VersionedTransaction.from_bytes(
                base64.b64decode(payload["params"][0])
            )
            signatures.append(str(transaction.signatures[0]))
            result = signatures[-1]
        elif method == "getSignatureStatuses":
            result = {"value": [{"err": None, "confirmationStatus": "confirmed"}]}
        else:
            raise AssertionError(f"unexpected RPC method: {method}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "result": result, "id": 1})

    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="mock",
        SOLANA_MODE="direct",
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        SOLANA_RPC_URL="https://rpc.test",
        SOLANA_PLATFORM_KEYPAIR=str(platform),
        SOLANA_AGENT_VAULT_KEYPAIR=str(vault),
        DEMO_STABLECOIN_MINT=str(stablecoin_mint),
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = DirectSolanaGateway(settings, http_client=client)
    issued = await gateway.issue_rwa(invoice_id="INV-2026-001")
    purchase = await gateway.purchase_rwa(
        invoice_id="INV-2026-001",
        rwa_mint_address=issued.mint_address,
        escrow_token_account=issued.escrow_token_account,
        supplier_wallet_address=str(supplier),
        amount_usdc=18_800,
    )
    await client.aclose()

    assert issued.transaction.status is TransactionStatus.CONFIRMED
    assert purchase.status is TransactionStatus.CONFIRMED
    assert purchase.provider == "DIRECT"
    assert len(signatures) == 2
