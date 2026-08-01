"""Solana USDC execution through Privy server wallets."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

import httpx
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.system_program import CreateAccountParams, create_account
from solders.transaction import VersionedTransaction
from spl.token.constants import MINT_LEN, TOKEN_PROGRAM_ID
from spl.token.instructions import (
    create_idempotent_associated_token_account,
    get_associated_token_address,
    initialize_mint,
    mint_to_checked,
    transfer_checked,
)
from spl.token.models import InitializeMintParams, MintToCheckedParams, TransferCheckedParams

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

    async def issue_rwa(self, *, invoice_id: str) -> RwaIssueResult: ...

    async def purchase_rwa(
        self,
        *,
        invoice_id: str,
        rwa_mint_address: str,
        escrow_token_account: str,
        supplier_wallet_address: str,
        amount_usdc: int,
    ) -> ChainTransferResult: ...

    async def prepare_vault_deposit(
        self, *, owner_wallet_address: str, amount_usdc: int
    ) -> PreparedVaultDeposit: ...

    async def verify_vault_deposit(
        self, *, signature: str, owner_wallet_address: str, amount_usdc: int
    ) -> bool: ...

    @property
    def vault_address(self) -> str: ...

    @property
    def stablecoin_mint_address(self) -> str: ...

    async def aclose(self) -> None:
        """Release network resources."""


@dataclass(frozen=True, slots=True)
class RwaIssueResult:
    mint_address: str
    escrow_token_account: str
    transaction: ChainTransferResult


@dataclass(frozen=True, slots=True)
class PreparedVaultDeposit:
    transaction_base64: str
    vault_address: str
    stablecoin_mint_address: str


class MockSolanaGateway:
    """Concurrency-safe deterministic chain adapter for local and stress tests."""

    mode = "mock"

    def __init__(self, settings: BackendSettings) -> None:
        self._settings = settings
        self._results: dict[str, ChainTransferResult] = {}
        self._lock = asyncio.Lock()

    @property
    def vault_address(self) -> str:
        return "DEMO_AGENT_VAULT"

    @property
    def stablecoin_mint_address(self) -> str:
        return "DEMO_STABLECOIN_MINT"

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

    async def issue_rwa(self, *, invoice_id: str) -> RwaIssueResult:
        result = await self.send_usdc(
            wallet_id="MOCK_PLATFORM",
            transfers=[ChainTransfer(to_address="DEMO_RWA_ESCROW", amount_usdc=0)],
            reference_id=f"rwa-issue-{invoice_id}",
        )
        digest = hashlib.sha256(invoice_id.encode("utf-8")).digest()
        escrow_digest = hashlib.sha256(digest + b"escrow").digest()
        return RwaIssueResult(
            mint_address=str(Pubkey.from_bytes(digest)),
            escrow_token_account=str(Pubkey.from_bytes(escrow_digest)),
            transaction=result,
        )

    async def purchase_rwa(
        self,
        *,
        invoice_id: str,
        rwa_mint_address: str,
        escrow_token_account: str,
        supplier_wallet_address: str,
        amount_usdc: int,
    ) -> ChainTransferResult:
        return await self.send_usdc(
            wallet_id="MOCK_AGENT_VAULT",
            transfers=[ChainTransfer(to_address=supplier_wallet_address, amount_usdc=amount_usdc)],
            reference_id=f"rwa-purchase-{invoice_id}",
        )

    async def prepare_vault_deposit(
        self, *, owner_wallet_address: str, amount_usdc: int
    ) -> PreparedVaultDeposit:
        payload = f"mock-deposit:{owner_wallet_address}:{amount_usdc}".encode()
        return PreparedVaultDeposit(
            transaction_base64=base64.b64encode(payload).decode("ascii"),
            vault_address=self.vault_address,
            stablecoin_mint_address=self.stablecoin_mint_address,
        )

    async def verify_vault_deposit(
        self, *, signature: str, owner_wallet_address: str, amount_usdc: int
    ) -> bool:
        return bool(signature and owner_wallet_address and amount_usdc > 0)


class DirectSolanaGateway:
    """Server-signed Devnet execution for the platform escrow and Agent Vault.

    Investor deposits stay non-custodial: the backend prepares a transaction and
    the connected investor wallet signs it in the browser.  Only the platform
    issuance escrow and the Agent Vault keys are loaded server-side.
    """

    mode = "direct"

    def __init__(
        self,
        settings: BackendSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        try:
            self._platform = Keypair.from_base58_string(settings.solana_platform_keypair or "")
            self._agent_vault = Keypair.from_base58_string(
                settings.solana_agent_vault_keypair or ""
            )
            self._stablecoin_mint = Pubkey.from_string(settings.demo_stablecoin_mint or "")
        except ValueError as exc:
            raise IntegrationError(
                "Devnet service wallet or stablecoin mint configuration is invalid"
            ) from exc
        self._client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(30))
        self._owns_client = http_client is None

    @property
    def vault_address(self) -> str:
        return str(self._agent_vault.pubkey())

    @property
    def stablecoin_mint_address(self) -> str:
        return str(self._stablecoin_mint)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def send_usdc(
        self, *, wallet_id: str, transfers: list[ChainTransfer], reference_id: str
    ) -> ChainTransferResult:
        if wallet_id not in {"AGENT_VAULT", "MOCK_TREASURY"}:
            raise IntegrationError("Direct Devnet mode can only execute from the Agent Vault")
        if len(transfers) != 1:
            raise IntegrationError("Direct Devnet funding requires exactly one recipient")
        transfer = transfers[0]
        supplier = Pubkey.from_string(transfer.to_address)
        source = get_associated_token_address(self._agent_vault.pubkey(), self._stablecoin_mint)
        destination = get_associated_token_address(supplier, self._stablecoin_mint)
        instructions = [
            create_idempotent_associated_token_account(
                payer=self._platform.pubkey(), owner=supplier, mint=self._stablecoin_mint
            ),
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=source,
                    mint=self._stablecoin_mint,
                    dest=destination,
                    owner=self._agent_vault.pubkey(),
                    amount=transfer.amount_usdc * 10**self._settings.solana_usdc_decimals,
                    decimals=self._settings.solana_usdc_decimals,
                )
            ),
        ]
        return await self._send_and_confirm(
            instructions=instructions,
            signers=[self._platform, self._agent_vault],
            from_address=self.vault_address,
            to_address=transfer.to_address,
        )

    async def issue_rwa(self, *, invoice_id: str) -> RwaIssueResult:
        mint = Keypair()
        rent = await self._minimum_rent(MINT_LEN)
        escrow = get_associated_token_address(self._platform.pubkey(), mint.pubkey())
        instructions = [
            create_account(
                CreateAccountParams(
                    from_pubkey=self._platform.pubkey(),
                    to_pubkey=mint.pubkey(),
                    lamports=rent,
                    space=MINT_LEN,
                    owner=TOKEN_PROGRAM_ID,
                )
            ),
            initialize_mint(
                InitializeMintParams(
                    decimals=0,
                    program_id=TOKEN_PROGRAM_ID,
                    mint=mint.pubkey(),
                    mint_authority=self._platform.pubkey(),
                )
            ),
            create_idempotent_associated_token_account(
                payer=self._platform.pubkey(), owner=self._platform.pubkey(), mint=mint.pubkey()
            ),
            mint_to_checked(
                MintToCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    mint=mint.pubkey(),
                    dest=escrow,
                    mint_authority=self._platform.pubkey(),
                    amount=1,
                    decimals=0,
                )
            ),
        ]
        transaction = await self._send_and_confirm(
            instructions=instructions,
            signers=[self._platform, mint],
            from_address=str(self._platform.pubkey()),
            to_address=str(escrow),
        )
        return RwaIssueResult(str(mint.pubkey()), str(escrow), transaction)

    async def purchase_rwa(
        self,
        *,
        invoice_id: str,
        rwa_mint_address: str,
        escrow_token_account: str,
        supplier_wallet_address: str,
        amount_usdc: int,
    ) -> ChainTransferResult:
        rwa_mint = Pubkey.from_string(rwa_mint_address)
        supplier = Pubkey.from_string(supplier_wallet_address)
        supplier_stable = get_associated_token_address(supplier, self._stablecoin_mint)
        vault_rwa = get_associated_token_address(self._agent_vault.pubkey(), rwa_mint)
        vault_stable = get_associated_token_address(
            self._agent_vault.pubkey(), self._stablecoin_mint
        )
        instructions = [
            create_idempotent_associated_token_account(
                payer=self._platform.pubkey(), owner=supplier, mint=self._stablecoin_mint
            ),
            create_idempotent_associated_token_account(
                payer=self._platform.pubkey(), owner=self._agent_vault.pubkey(), mint=rwa_mint
            ),
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=vault_stable,
                    mint=self._stablecoin_mint,
                    dest=supplier_stable,
                    owner=self._agent_vault.pubkey(),
                    amount=amount_usdc * 10**self._settings.solana_usdc_decimals,
                    decimals=self._settings.solana_usdc_decimals,
                )
            ),
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=Pubkey.from_string(escrow_token_account),
                    mint=rwa_mint,
                    dest=vault_rwa,
                    owner=self._platform.pubkey(),
                    amount=1,
                    decimals=0,
                )
            ),
        ]
        return await self._send_and_confirm(
            instructions=instructions,
            signers=[self._platform, self._agent_vault],
            from_address=self.vault_address,
            to_address=supplier_wallet_address,
        )

    async def prepare_vault_deposit(
        self, *, owner_wallet_address: str, amount_usdc: int
    ) -> PreparedVaultDeposit:
        owner = Pubkey.from_string(owner_wallet_address)
        source = get_associated_token_address(owner, self._stablecoin_mint)
        destination = get_associated_token_address(
            self._agent_vault.pubkey(), self._stablecoin_mint
        )
        instructions = [
            create_idempotent_associated_token_account(
                payer=owner, owner=self._agent_vault.pubkey(), mint=self._stablecoin_mint
            ),
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=source,
                    mint=self._stablecoin_mint,
                    dest=destination,
                    owner=owner,
                    amount=amount_usdc * 10**self._settings.solana_usdc_decimals,
                    decimals=self._settings.solana_usdc_decimals,
                )
            ),
        ]
        blockhash = Hash.from_string(await self._latest_blockhash())
        message = MessageV0.try_compile(owner, instructions, [], blockhash)
        transaction = VersionedTransaction.populate(message, [Signature.default()])
        return PreparedVaultDeposit(
            transaction_base64=base64.b64encode(bytes(transaction)).decode("ascii"),
            vault_address=self.vault_address,
            stablecoin_mint_address=self.stablecoin_mint_address,
        )

    async def verify_vault_deposit(
        self, *, signature: str, owner_wallet_address: str, amount_usdc: int
    ) -> bool:
        payload = await self._rpc(
            "getTransaction",
            [signature, {"encoding": "jsonParsed", "commitment": "confirmed"}],
        )
        if payload is None:
            return False
        meta = payload.get("meta") if isinstance(payload, dict) else None
        if not isinstance(meta, dict) or meta.get("err") is not None:
            return False
        destination = str(
            get_associated_token_address(self._agent_vault.pubkey(), self._stablecoin_mint)
        )
        transaction = payload.get("transaction") if isinstance(payload, dict) else None
        message = transaction.get("message") if isinstance(transaction, dict) else None
        instructions = message.get("instructions", []) if isinstance(message, dict) else []
        balances = meta.get("postTokenBalances", []) if isinstance(meta, dict) else []
        expected_raw = amount_usdc * 10**self._settings.solana_usdc_decimals
        destination_has_expected_balance = any(
            isinstance(balance, dict)
            and balance.get("accountIndex") is not None
            and balance.get("owner") == self.vault_address
            and balance.get("mint") == self.stablecoin_mint_address
            and int((balance.get("uiTokenAmount") or {}).get("amount") or 0) >= expected_raw
            for balance in balances
        )
        has_expected_transfer = any(
            isinstance(instruction, dict)
            and instruction.get("program") in {"spl-token", "spl-token-2022"}
            and isinstance(instruction.get("parsed"), dict)
            and instruction["parsed"].get("type") in {"transfer", "transferChecked"}
            and isinstance(instruction["parsed"].get("info"), dict)
            and instruction["parsed"]["info"].get("authority") == owner_wallet_address
            and instruction["parsed"]["info"].get("destination") == destination
            and int(
                (
                    instruction["parsed"]["info"].get("tokenAmount")
                    or {"amount": instruction["parsed"]["info"].get("amount", 0)}
                ).get("amount", 0)
            )
            == expected_raw
            for instruction in instructions
        )
        return destination_has_expected_balance and has_expected_transfer

    async def _send_and_confirm(
        self, *, instructions: list[Any], signers: list[Keypair], from_address: str, to_address: str
    ) -> ChainTransferResult:
        blockhash = Hash.from_string(await self._latest_blockhash())
        message = MessageV0.try_compile(self._platform.pubkey(), instructions, [], blockhash)
        transaction = VersionedTransaction(message, signers)
        serialized = base64.b64encode(bytes(transaction)).decode("ascii")
        signature = await self._rpc(
            "sendTransaction",
            [
                serialized,
                {"encoding": "base64", "preflightCommitment": "confirmed"},
            ],
        )
        if not isinstance(signature, str) or not signature:
            raise IntegrationError("Solana RPC did not return a transaction signature")
        status = await self._confirmation_status(signature)
        return ChainTransferResult(
            signature=signature,
            status=status,
            from_address=from_address,
            provider="DIRECT",
            sandbox=False,
        )

    async def _minimum_rent(self, size: int) -> int:
        value = await self._rpc("getMinimumBalanceForRentExemption", [size])
        if not isinstance(value, int):
            raise IntegrationError("Solana RPC did not return the mint rent exemption")
        return value

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

    async def _rpc(self, method: str, params: list[object]) -> Any:
        response = await self._client.post(
            self._settings.solana_rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            headers={"content-type": "application/json"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise IntegrationError(
                f"Solana RPC {method} failed with HTTP {response.status_code}"
            ) from exc
        payload = response.json()
        if payload.get("error") is not None:
            raise IntegrationError(f"Solana RPC {method} returned an error")
        return payload.get("result")


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

    @property
    def vault_address(self) -> str:
        return self._settings.investor_settlement_wallet_address

    @property
    def stablecoin_mint_address(self) -> str:
        return self._settings.solana_usdc_mint

    async def issue_rwa(self, *, invoice_id: str) -> RwaIssueResult:
        raise IntegrationError("RWA 발행은 SOLANA_MODE=direct에서만 지원합니다.")

    async def purchase_rwa(
        self,
        *,
        invoice_id: str,
        rwa_mint_address: str,
        escrow_token_account: str,
        supplier_wallet_address: str,
        amount_usdc: int,
    ) -> ChainTransferResult:
        raise IntegrationError("RWA 자동 매수는 SOLANA_MODE=direct에서만 지원합니다.")

    async def prepare_vault_deposit(
        self, *, owner_wallet_address: str, amount_usdc: int
    ) -> PreparedVaultDeposit:
        raise IntegrationError("Agent Vault 예치는 SOLANA_MODE=direct에서만 지원합니다.")

    async def verify_vault_deposit(
        self, *, signature: str, owner_wallet_address: str, amount_usdc: int
    ) -> bool:
        return False

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

        from_address = await self._wallet_address(wallet_id)
        serialized_transaction = await self._build_transaction(from_address, transfers)
        response = await self._client.post(
            f"{self._settings.privy_api_base_url}/v1/wallets/{wallet_id}/rpc",
            json={
                "method": "signAndSendTransaction",
                "caip2": self._settings.solana_caip2,
                "sponsor": self._settings.privy_sponsor,
                "params": {
                    "transaction": base64.b64encode(serialized_transaction).decode("ascii"),
                    "encoding": "base64",
                },
                "reference_id": reference_id,
            },
        )
        self._raise_for_provider_error(response, "Privy signAndSendTransaction")
        payload = response.json()
        try:
            signature = str(payload["data"]["hash"])
        except (KeyError, TypeError) as exc:
            raise IntegrationError("Privy response did not contain a transaction hash") from exc
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
            raise IntegrationError(f"{operation} failed with HTTP {response.status_code}") from exc


def create_solana_gateway(settings: BackendSettings) -> SolanaGateway:
    """Select a direct Devnet adapter only when explicitly configured."""

    if settings.resolved_solana_mode() == "direct":
        return DirectSolanaGateway(settings)
    if settings.resolved_solana_mode() == "privy":
        return PrivySolanaGateway(settings)
    return MockSolanaGateway(settings)
