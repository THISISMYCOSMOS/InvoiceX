"""Solana USDC execution through Privy server wallets."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import time
from decimal import Decimal
from typing import Protocol

import httpx
from solders.hash import Hash
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    create_idempotent_associated_token_account,
    get_associated_token_address,
    transfer_checked,
)
from spl.token.models import TransferCheckedParams

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import IntegrationError
from invoicex_backend.models import (
    ChainTransfer,
    ChainTransferResult,
    TransactionStatus,
)


class SolanaGateway(Protocol):
    """Provider-neutral blockchain execution boundary."""

    mode: str

    async def send_usdc(
        self,
        *,
        wallet_id: str,
        transfers: list[ChainTransfer],
        reference_id: str,
    ) -> ChainTransferResult:
        """Sign, broadcast, and confirm one idempotent USDC transaction."""

    async def aclose(self) -> None:
        """Release network resources."""


class MockSolanaGateway:
    """Concurrency-safe deterministic chain adapter for local and stress tests."""

    mode = "mock"

    def __init__(self, settings: BackendSettings) -> None:
        self._settings = settings
        self._results: dict[str, ChainTransferResult] = {}
        self._lock = asyncio.Lock()

    async def send_usdc(
        self,
        *,
        wallet_id: str,
        transfers: list[ChainTransfer],
        reference_id: str,
    ) -> ChainTransferResult:
        if not transfers:
            raise IntegrationError("USDC transfer requires at least one destination")
        async with self._lock:
            existing = self._results.get(reference_id)
            if existing is not None:
                return existing

            digest = hashlib.sha512(reference_id.encode("utf-8")).digest()
            result = ChainTransferResult(
                signature=str(Signature.from_bytes(digest)),
                status=TransactionStatus.CONFIRMED,
                from_address=(
                    "DEMO_SETTLEMENT_PARTNER"
                    if wallet_id == self._settings.privy_settlement_wallet_id
                    else "DEMO_AGENT_VAULT"
                ),
                provider="MOCK",
                sandbox=True,
            )
            self._results[reference_id] = result
            return result

    async def aclose(self) -> None:
        return None


class PrivySolanaGateway:
    """Build SPL-token transactions and execute them with Privy's REST API."""

    mode = "privy"

    def __init__(
        self,
        settings: BackendSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(30),
            auth=httpx.BasicAuth(
                settings.privy_app_id or "",
                settings.privy_app_secret or "",
            ),
            headers={
                "privy-app-id": settings.privy_app_id or "",
                "content-type": "application/json",
            },
        )
        self._owns_client = http_client is None
        self._wallet_addresses: dict[str, str] = {}
        self._wallet_lock = asyncio.Lock()

    async def send_usdc(
        self,
        *,
        wallet_id: str,
        transfers: list[ChainTransfer],
        reference_id: str,
    ) -> ChainTransferResult:
        if not transfers:
            raise IntegrationError("USDC transfer requires at least one destination")
        if len(reference_id) > 64:
            raise IntegrationError("Privy reference_id must not exceed 64 characters")

        try:
            from_address = await self._wallet_address(wallet_id)
            serialized_transaction = await self._build_transaction(
                from_address,
                transfers,
            )
            response = await self._client.post(
                f"{self._settings.privy_api_base_url}/v1/wallets/{wallet_id}/rpc",
                headers={"privy-idempotency-key": f"invoicex:{reference_id}"},
                json={
                    "method": "signAndSendTransaction",
                    "caip2": self._settings.solana_caip2,
                    "sponsor": self._settings.privy_sponsor,
                    "params": {
                        "transaction": base64.b64encode(
                            serialized_transaction
                        ).decode("ascii"),
                        "encoding": "base64",
                    },
                    "reference_id": reference_id,
                },
            )
            self._raise_for_provider_error(response, "Privy signAndSendTransaction")
            payload = response.json()
            signature = str(payload["data"]["hash"])
        except (KeyError, TypeError) as exc:
            raise IntegrationError("Privy response did not contain a transaction hash") from exc
        except httpx.HTTPError as exc:
            raise IntegrationError("Privy or Solana network request failed") from exc
        except ValueError as exc:
            raise IntegrationError(
                "Privy/Solana returned invalid data or an address is invalid"
            ) from exc
        if not signature:
            raise IntegrationError(
                "Privy returned an empty transaction hash; custodial screening is still pending"
            )

        status = await self._confirmation_status(signature)
        return ChainTransferResult(
            signature=signature,
            status=status,
            from_address=from_address,
            provider="PRIVY",
            sandbox=False,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _wallet_address(self, wallet_id: str) -> str:
        cached = self._wallet_addresses.get(wallet_id)
        if cached is not None:
            return cached
        async with self._wallet_lock:
            cached = self._wallet_addresses.get(wallet_id)
            if cached is not None:
                return cached
            response = await self._client.get(
                f"{self._settings.privy_api_base_url}/v1/wallets/{wallet_id}"
            )
            self._raise_for_provider_error(response, "Privy get wallet")
            payload = response.json()
            if payload.get("chain_type") != "solana":
                raise IntegrationError("Configured Privy wallet is not a Solana wallet")
            address = payload.get("address")
            if not isinstance(address, str) or not address:
                raise IntegrationError("Privy wallet response did not contain an address")
            try:
                Pubkey.from_string(address)
            except ValueError as exc:
                raise IntegrationError("Privy returned an invalid Solana wallet address") from exc
            self._wallet_addresses[wallet_id] = address
            return address

    async def _build_transaction(
        self,
        from_address: str,
        transfers: list[ChainTransfer],
    ) -> bytes:
        owner = Pubkey.from_string(from_address)
        mint = Pubkey.from_string(self._settings.solana_usdc_mint)
        source_account = get_associated_token_address(owner, mint, TOKEN_PROGRAM_ID)
        instructions = []
        scale = Decimal(10) ** self._settings.solana_usdc_decimals
        for transfer in transfers:
            destination_owner = Pubkey.from_string(transfer.to_address)
            destination_account = get_associated_token_address(
                destination_owner,
                mint,
                TOKEN_PROGRAM_ID,
            )
            instructions.append(
                create_idempotent_associated_token_account(
                    payer=owner,
                    owner=destination_owner,
                    mint=mint,
                    token_program_id=TOKEN_PROGRAM_ID,
                )
            )
            instructions.append(
                transfer_checked(
                    TransferCheckedParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=source_account,
                        mint=mint,
                        dest=destination_account,
                        owner=owner,
                        amount=int(Decimal(transfer.amount_usdc) * scale),
                        decimals=self._settings.solana_usdc_decimals,
                    )
                )
            )

        recent_blockhash = Hash.from_string(await self._latest_blockhash())
        message = MessageV0.try_compile(
            payer=owner,
            instructions=instructions,
            address_lookup_table_accounts=[],
            recent_blockhash=recent_blockhash,
        )
        unsigned = VersionedTransaction.populate(message, [Signature.default()])
        return bytes(unsigned)

    async def _latest_blockhash(self) -> str:
        payload = await self._rpc("getLatestBlockhash", [{"commitment": "confirmed"}])
        try:
            return str(payload["value"]["blockhash"])
        except (KeyError, TypeError) as exc:
            raise IntegrationError("Solana RPC did not return a recent blockhash") from exc

    async def _confirmation_status(self, signature: str) -> TransactionStatus:
        deadline = time.monotonic() + self._settings.solana_confirmation_timeout_seconds
        while time.monotonic() < deadline:
            payload = await self._rpc(
                "getSignatureStatuses",
                [[signature], {"searchTransactionHistory": True}],
            )
            values = payload.get("value") if isinstance(payload, dict) else None
            status = values[0] if isinstance(values, list) and values else None
            if isinstance(status, dict):
                if status.get("err") is not None:
                    raise IntegrationError("Solana transaction was rejected on-chain")
                if status.get("confirmationStatus") in {"confirmed", "finalized"}:
                    return TransactionStatus.CONFIRMED
            await asyncio.sleep(0.5)
        return TransactionStatus.PENDING

    async def _rpc(self, method: str, params: list[object]) -> dict[str, object]:
        response = await self._client.post(
            self._settings.solana_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params,
            },
            auth=None,
            headers={"content-type": "application/json"},
        )
        self._raise_for_provider_error(response, f"Solana RPC {method}")
        payload = response.json()
        if payload.get("error") is not None:
            raise IntegrationError(f"Solana RPC {method} returned an error")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise IntegrationError(f"Solana RPC {method} returned an invalid result")
        return result

    @staticmethod
    def _raise_for_provider_error(response: httpx.Response, operation: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise IntegrationError(
                f"{operation} failed with HTTP {response.status_code}"
            ) from exc


def create_solana_gateway(settings: BackendSettings) -> SolanaGateway:
    """Select the real Privy/Solana adapter only when fully configured."""

    if settings.resolved_solana_mode() == "privy":
        return PrivySolanaGateway(settings)
    return MockSolanaGateway(settings)
