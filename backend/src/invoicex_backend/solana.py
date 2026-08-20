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
from solders.compute_budget import ID as COMPUTE_BUDGET_PROGRAM_ID
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import MessageV0, to_bytes_versioned
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.system_program import CreateAccountParams, create_account
from solders.transaction import VersionedTransaction
from spl.token.constants import MINT_LEN, TOKEN_PROGRAM_ID
from spl.token.instructions import (
    AuthorityType,
    create_idempotent_associated_token_account,
    get_associated_token_address,
    initialize_mint,
    mint_to_checked,
    set_authority,
    transfer_checked,
)
from spl.token.models import (
    InitializeMintParams,
    MintToCheckedParams,
    SetAuthorityParams,
    TransferCheckedParams,
)

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

    async def settlement_wallet_address(self) -> str: ...

    async def verify_usdc_payment(
        self,
        *,
        signature: str,
        sender_wallet_address: str,
        recipient_wallet_address: str,
        amount_usdc: int,
    ) -> bool: ...

    async def sponsor_vault_deposit(
        self,
        *,
        owner_wallet_address: str,
        amount_usdc: int,
        prepared_transaction_base64: str,
        signed_transaction_base64: str,
        reference_id: str,
    ) -> ChainTransferResult: ...

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
    sponsored: bool = False
    sponsor_deposit_id: str | None = None
    sponsor_wallet_address: str | None = None


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

    async def settlement_wallet_address(self) -> str:
        return "DEMO_SETTLEMENT_WALLET"

    async def verify_usdc_payment(
        self,
        *,
        signature: str,
        sender_wallet_address: str,
        recipient_wallet_address: str,
        amount_usdc: int,
    ) -> bool:
        return bool(
            signature
            and sender_wallet_address
            and recipient_wallet_address == await self.settlement_wallet_address()
            and amount_usdc > 0
        )

    async def sponsor_vault_deposit(self, **_: Any) -> ChainTransferResult:
        raise IntegrationError("가스리스 예치는 Privy Devnet 설정 후 사용할 수 있습니다.")


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
            set_authority(
                SetAuthorityParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=mint.pubkey(),
                    authority=AuthorityType.MINT_TOKENS,
                    current_authority=self._platform.pubkey(),
                    signers=[],
                    new_authority=None,
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
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "commitment": "confirmed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
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

    async def settlement_wallet_address(self) -> str:
        # Buyer repayments must land in the same Agent Vault that later sends
        # the investor payout. The platform wallet only sponsors ATA creation
        # and transaction fees; it is not a custody destination for USDC.
        return self.vault_address

    async def verify_usdc_payment(
        self,
        *,
        signature: str,
        sender_wallet_address: str,
        recipient_wallet_address: str,
        amount_usdc: int,
    ) -> bool:
        payload = await self._rpc(
            "getTransaction",
            [signature, {"encoding": "jsonParsed", "commitment": "confirmed", "maxSupportedTransactionVersion": 0}],
        )
        return self._payment_matches(
            payload,
            sender_wallet_address=sender_wallet_address,
            recipient_wallet_address=recipient_wallet_address,
            amount_usdc=amount_usdc,
        )

    def _payment_matches(
        self,
        payload: object,
        *,
        sender_wallet_address: str,
        recipient_wallet_address: str,
        amount_usdc: int,
    ) -> bool:
        if not isinstance(payload, dict):
            return False
        meta = payload.get("meta")
        if not isinstance(meta, dict) or meta.get("err") is not None:
            return False
        transaction = payload.get("transaction")
        message = transaction.get("message") if isinstance(transaction, dict) else None
        instructions = message.get("instructions", []) if isinstance(message, dict) else []
        expected_destination = str(
            get_associated_token_address(
                Pubkey.from_string(recipient_wallet_address), self._stablecoin_mint
            )
        )
        expected_raw = amount_usdc * 10**self._settings.solana_usdc_decimals
        return any(
            isinstance(instruction, dict)
            and instruction.get("program") in {"spl-token", "spl-token-2022"}
            and isinstance(instruction.get("parsed"), dict)
            and instruction["parsed"].get("type") in {"transfer", "transferChecked"}
            and isinstance(instruction["parsed"].get("info"), dict)
            and instruction["parsed"]["info"].get("authority") == sender_wallet_address
            and instruction["parsed"]["info"].get("destination") == expected_destination
            and int((instruction["parsed"]["info"].get("tokenAmount") or {"amount": instruction["parsed"]["info"].get("amount", 0)}).get("amount", 0)) == expected_raw
            for instruction in instructions
        )

    async def sponsor_vault_deposit(self, **_: Any) -> ChainTransferResult:
        raise IntegrationError("가스리스 예치는 Privy Sponsor 지갑이 필요합니다.")

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
    """Execute Circle Devnet USDC and invoice RWA transactions via Privy wallets.

    The Treasury wallet owns deposited USDC.  A separate Privy issuer wallet
    holds each freshly minted RWA in escrow, so the agent can exchange the two
    assets in one transaction signed by both service wallets.
    """

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
        issuer_wallet_id = self._require_issuer_wallet_id()
        issuer = Pubkey.from_string(await self._wallet_address(issuer_wallet_id))
        fee_payer, fee_payer_wallet_id = await self._platform_fee_payer(fallback=issuer)
        mint = Keypair()
        rent = await self._minimum_rent(MINT_LEN)
        escrow = get_associated_token_address(issuer, mint.pubkey())
        instructions = [
            create_account(
                CreateAccountParams(
                    from_pubkey=fee_payer,
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
                    mint_authority=issuer,
                )
            ),
            create_idempotent_associated_token_account(
                payer=fee_payer,
                owner=issuer,
                mint=mint.pubkey(),
            ),
            mint_to_checked(
                MintToCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    mint=mint.pubkey(),
                    dest=escrow,
                    mint_authority=issuer,
                    amount=1,
                    decimals=0,
                )
            ),
            set_authority(
                SetAuthorityParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=mint.pubkey(),
                    authority=AuthorityType.MINT_TOKENS,
                    current_authority=issuer,
                    signers=[],
                    new_authority=None,
                )
            ),
        ]
        transaction = await self._partially_signed_transaction(
            payer=fee_payer,
            instructions=instructions,
            additional_signers=[mint],
        )
        if fee_payer_wallet_id is None:
            result = await self._sign_and_send(
                wallet_id=issuer_wallet_id,
                transaction=transaction,
                reference_id=f"rwa-issue-{invoice_id}",
            )
        else:
            issuer_signed = await self._sign_transaction(
                wallet_id=issuer_wallet_id,
                transaction=transaction,
            )
            result = await self._sign_and_send(
                wallet_id=fee_payer_wallet_id,
                transaction=issuer_signed,
                reference_id=f"rwa-issue-{invoice_id}",
                from_address=str(issuer),
            )
        return RwaIssueResult(
            mint_address=str(mint.pubkey()),
            escrow_token_account=str(escrow),
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
        if amount_usdc <= 0:
            raise IntegrationError("RWA 자동 매수 금액이 올바르지 않습니다.")
        issuer_wallet_id = self._require_issuer_wallet_id()
        treasury = Pubkey.from_string(await self._treasury_address())
        issuer = Pubkey.from_string(await self._wallet_address(issuer_wallet_id))
        fee_payer, fee_payer_wallet_id = await self._platform_fee_payer(fallback=treasury)
        supplier = Pubkey.from_string(supplier_wallet_address)
        stablecoin_mint = Pubkey.from_string(self.stablecoin_mint_address)
        rwa_mint = Pubkey.from_string(rwa_mint_address)
        treasury_usdc = get_associated_token_address(treasury, stablecoin_mint)
        supplier_usdc = get_associated_token_address(supplier, stablecoin_mint)
        treasury_rwa = get_associated_token_address(treasury, rwa_mint)
        instructions = [
            create_idempotent_associated_token_account(
                payer=fee_payer,
                owner=supplier,
                mint=stablecoin_mint,
            ),
            create_idempotent_associated_token_account(
                payer=fee_payer,
                owner=treasury,
                mint=rwa_mint,
            ),
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=treasury_usdc,
                    mint=stablecoin_mint,
                    dest=supplier_usdc,
                    owner=treasury,
                    amount=amount_usdc * 10**self._settings.solana_usdc_decimals,
                    decimals=self._settings.solana_usdc_decimals,
                )
            ),
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=Pubkey.from_string(escrow_token_account),
                    mint=rwa_mint,
                    dest=treasury_rwa,
                    owner=issuer,
                    amount=1,
                    decimals=0,
                )
            ),
        ]
        transaction = await self._partially_signed_transaction(
            payer=fee_payer,
            instructions=instructions,
            additional_signers=[],
        )
        issuer_signed = await self._sign_transaction(
            wallet_id=issuer_wallet_id,
            transaction=transaction,
        )
        if fee_payer_wallet_id is not None:
            treasury_signed = await self._sign_transaction(
                wallet_id=self._settings.privy_treasury_wallet_id or "",
                transaction=issuer_signed,
            )
            return await self._sign_and_send(
                wallet_id=fee_payer_wallet_id,
                transaction=treasury_signed,
                reference_id=f"rwa-purchase-{invoice_id}",
                from_address=str(treasury),
            )
        return await self._sign_and_send(
            wallet_id=self._settings.privy_treasury_wallet_id or "",
            transaction=issuer_signed,
            reference_id=f"rwa-purchase-{invoice_id}",
            from_address=str(treasury),
        )

    async def prepare_vault_deposit(
        self, *, owner_wallet_address: str, amount_usdc: int
    ) -> PreparedVaultDeposit:
        owner = Pubkey.from_string(owner_wallet_address)
        treasury = Pubkey.from_string(await self._treasury_address())
        sponsor = (
            Pubkey.from_string(await self._sponsor_address())
            if self._settings.gasless_enabled
            else owner
        )
        mint = Pubkey.from_string(self.stablecoin_mint_address)
        source = get_associated_token_address(owner, mint)
        destination = get_associated_token_address(treasury, mint)
        instructions = [
            create_idempotent_associated_token_account(
                payer=sponsor,
                owner=treasury,
                mint=mint,
            ),
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=source,
                    mint=mint,
                    dest=destination,
                    owner=owner,
                    amount=amount_usdc * 10**self._settings.solana_usdc_decimals,
                    decimals=self._settings.solana_usdc_decimals,
                )
            ),
        ]
        transaction = await self._unsigned_transaction(payer=sponsor, instructions=instructions)
        return PreparedVaultDeposit(
            transaction_base64=base64.b64encode(bytes(transaction)).decode("ascii"),
            vault_address=str(treasury),
            stablecoin_mint_address=self.stablecoin_mint_address,
            sponsored=self._settings.gasless_enabled,
            sponsor_wallet_address=str(sponsor) if self._settings.gasless_enabled else None,
        )

    async def sponsor_vault_deposit(
        self,
        *,
        owner_wallet_address: str,
        amount_usdc: int,
        prepared_transaction_base64: str,
        signed_transaction_base64: str,
        reference_id: str,
    ) -> ChainTransferResult:
        if not self._settings.gasless_enabled:
            raise IntegrationError("가스리스 예치가 활성화되어 있지 않습니다.")
        try:
            expected = VersionedTransaction.from_bytes(
                base64.b64decode(prepared_transaction_base64, validate=True)
            )
            submitted = VersionedTransaction.from_bytes(
                base64.b64decode(signed_transaction_base64, validate=True)
            )
        except ValueError as exc:
            raise IntegrationError("가스리스 예치 서명 트랜잭션 형식이 올바르지 않습니다.") from exc
        if not self._has_same_vault_deposit_effect(expected, submitted):
            raise IntegrationError(
                "승인된 Agent Vault 예치 내용과 서명 트랜잭션이 일치하지 않습니다."
            )
        sponsor = await self._sponsor_address()
        if not submitted.message.account_keys or str(submitted.message.account_keys[0]) != sponsor:
            raise IntegrationError("가스리스 수수료 지갑이 올바르지 않습니다.")
        owner = Pubkey.from_string(owner_wallet_address)
        try:
            owner_index = list(submitted.message.account_keys).index(owner)
            owner_signature = submitted.signatures[owner_index]
        except (ValueError, IndexError) as exc:
            raise IntegrationError("투자자 지갑 서명이 예치 트랜잭션에 없습니다.") from exc
        signature_is_valid = owner_signature.verify(owner, to_bytes_versioned(submitted.message))
        if owner_signature == Signature.default() or not signature_is_valid:
            raise IntegrationError("투자자 지갑 서명을 검증하지 못했습니다.")
        return await self._sign_and_send(
            wallet_id=self._settings.privy_sponsor_wallet_id or "",
            transaction=bytes(submitted),
            reference_id=reference_id,
            from_address=owner_wallet_address,
        )

    @staticmethod
    def _has_same_vault_deposit_effect(
        expected: VersionedTransaction,
        submitted: VersionedTransaction,
    ) -> bool:
        """Compare the resolved on-chain effects of a sponsored deposit message.

        Browser wallets are allowed to refresh a recent blockhash while signing
        a versioned transaction and may recompile the static account-key order or
        add bounded Compute Budget instructions.  Those changes do not alter the
        approved token transfer, so compare instructions after resolving their
        account indexes to public keys instead of comparing compiled indexes.

        Address lookup tables remain forbidden for this small deposit transaction.
        Optional priority-fee instructions are accepted only within a conservative
        sponsor cost cap.
        """

        expected_message = expected.message
        submitted_message = submitted.message
        if expected_message.address_table_lookups or submitted_message.address_table_lookups:
            return False

        expected_effect = PrivySolanaGateway._resolved_instruction_effects(
            expected_message,
            allow_compute_budget=False,
        )
        submitted_effect = PrivySolanaGateway._resolved_instruction_effects(
            submitted_message,
            allow_compute_budget=True,
        )
        return expected_effect is not None and expected_effect == submitted_effect

    @staticmethod
    def _resolved_instruction_effects(
        message: MessageV0,
        *,
        allow_compute_budget: bool,
    ) -> tuple[tuple[str, tuple[str, ...], bytes], ...] | None:
        """Resolve compiled instruction indexes and reject unsafe wallet additions."""

        account_keys = list(message.account_keys)
        effects: list[tuple[str, tuple[str, ...], bytes]] = []
        compute_unit_limit = 200_000
        compute_unit_price = 0
        try:
            for instruction in message.instructions:
                program_id = account_keys[instruction.program_id_index]
                data = bytes(instruction.data)
                if program_id == COMPUTE_BUDGET_PROGRAM_ID:
                    if not allow_compute_budget:
                        return None
                    if len(data) == 5 and data[0] == 2:
                        compute_unit_limit = int.from_bytes(data[1:], "little")
                        if not 1 <= compute_unit_limit <= 400_000:
                            return None
                        continue
                    if len(data) == 9 and data[0] == 3:
                        compute_unit_price = int.from_bytes(data[1:], "little")
                        continue
                    return None
                resolved_accounts = tuple(
                    str(account_keys[account_index]) for account_index in instruction.accounts
                )
                effects.append((str(program_id), resolved_accounts, data))
        except (IndexError, ValueError):
            return None

        # micro-lamports per compute unit -> lamports, rounded up.  The wallet may
        # request priority processing, but it cannot charge the Sponsor over 0.0002 SOL.
        priority_fee_lamports = (
            compute_unit_limit * compute_unit_price + 1_000_000 - 1
        ) // 1_000_000
        if priority_fee_lamports > 200_000:
            return None
        return tuple(effects)

    async def verify_vault_deposit(
        self, *, signature: str, owner_wallet_address: str, amount_usdc: int
    ) -> bool:
        payload = await self._rpc(
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "commitment": "confirmed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        )
        if payload is None:
            return False
        meta = payload.get("meta") if isinstance(payload, dict) else None
        if not isinstance(meta, dict) or meta.get("err") is not None:
            return False
        treasury = await self._treasury_address()
        destination = str(
            get_associated_token_address(
                Pubkey.from_string(treasury),
                Pubkey.from_string(self.stablecoin_mint_address),
            )
        )
        transaction = payload.get("transaction") if isinstance(payload, dict) else None
        message = transaction.get("message") if isinstance(transaction, dict) else None
        instructions = message.get("instructions", []) if isinstance(message, dict) else []
        expected_raw = amount_usdc * 10**self._settings.solana_usdc_decimals
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
        pre_balances = meta.get("preTokenBalances", [])
        post_balances = meta.get("postTokenBalances", [])
        owner_delta = self._token_balance_delta(
            pre_balances,
            post_balances,
            owner_wallet_address,
        )
        treasury_delta = self._token_balance_delta(pre_balances, post_balances, treasury)
        return (
            has_expected_transfer
            and owner_delta == -expected_raw
            and treasury_delta == expected_raw
        )

    async def settlement_wallet_address(self) -> str:
        wallet_id = self._settings.privy_settlement_wallet_id
        if not wallet_id:
            raise IntegrationError("PRIVY_SETTLEMENT_WALLET_ID가 설정되지 않았습니다.")
        return await self._wallet_address(wallet_id)

    async def verify_usdc_payment(
        self,
        *,
        signature: str,
        sender_wallet_address: str,
        recipient_wallet_address: str,
        amount_usdc: int,
    ) -> bool:
        payload = await self._rpc(
            "getTransaction",
            [signature, {"encoding": "jsonParsed", "commitment": "confirmed", "maxSupportedTransactionVersion": 0}],
        )
        if not isinstance(payload, dict):
            return False
        meta = payload.get("meta")
        if not isinstance(meta, dict) or meta.get("err") is not None:
            return False
        transaction = payload.get("transaction")
        message = transaction.get("message") if isinstance(transaction, dict) else None
        instructions = message.get("instructions", []) if isinstance(message, dict) else []
        mint = Pubkey.from_string(self.stablecoin_mint_address)
        destination = str(
            get_associated_token_address(Pubkey.from_string(recipient_wallet_address), mint)
        )
        expected_raw = amount_usdc * 10**self._settings.solana_usdc_decimals
        has_transfer = any(
            isinstance(instruction, dict)
            and instruction.get("program") in {"spl-token", "spl-token-2022"}
            and isinstance(instruction.get("parsed"), dict)
            and instruction["parsed"].get("type") in {"transfer", "transferChecked"}
            and isinstance(instruction["parsed"].get("info"), dict)
            and instruction["parsed"]["info"].get("authority") == sender_wallet_address
            and instruction["parsed"]["info"].get("destination") == destination
            and int((instruction["parsed"]["info"].get("tokenAmount") or {"amount": instruction["parsed"]["info"].get("amount", 0)}).get("amount", 0)) == expected_raw
            for instruction in instructions
        )
        pre_balances = meta.get("preTokenBalances", [])
        post_balances = meta.get("postTokenBalances", [])
        return (
            has_transfer
            and self._token_balance_delta(pre_balances, post_balances, sender_wallet_address) == -expected_raw
            and self._token_balance_delta(pre_balances, post_balances, recipient_wallet_address) == expected_raw
        )

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
        return await self._sign_and_send(
            wallet_id=wallet_id,
            transaction=serialized_transaction,
            reference_id=reference_id,
            from_address=from_address,
        )

    async def fund_development_wallet(
        self,
        *,
        recipient_wallet_address: str,
        amount_usdc: int,
        reference_id: str,
    ) -> ChainTransferResult:
        """Fund one external Devnet wallet from Agent Vault for local demos only.

        This intentionally stays off the public API surface.  It is used by a
        developer-run CLI when a test faucet is rate-limited.  The Treasury
        wallet authorizes the USDC transfer, while the Sponsor wallet remains
        the transaction fee payer whenever gasless mode is enabled.
        """

        if amount_usdc <= 0:
            raise IntegrationError("개발용 지급 USDC 금액이 올바르지 않습니다.")
        if amount_usdc > self._settings.solana_demo_transfer_amount_usdc:
            raise IntegrationError("개발용 지급은 데모 전송 한도를 초과할 수 없습니다.")

        try:
            recipient = Pubkey.from_string(recipient_wallet_address)
        except ValueError as exc:
            raise IntegrationError("개발용 지급 대상 지갑 주소가 올바르지 않습니다.") from exc

        treasury = Pubkey.from_string(await self._treasury_address())
        fee_payer, fee_payer_wallet_id = await self._platform_fee_payer(fallback=treasury)
        mint = Pubkey.from_string(self.stablecoin_mint_address)
        treasury_usdc = get_associated_token_address(treasury, mint)
        recipient_usdc = get_associated_token_address(recipient, mint)
        instructions = [
            create_idempotent_associated_token_account(
                payer=fee_payer,
                owner=recipient,
                mint=mint,
            ),
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=treasury_usdc,
                    mint=mint,
                    dest=recipient_usdc,
                    owner=treasury,
                    amount=amount_usdc * 10**self._settings.solana_usdc_decimals,
                    decimals=self._settings.solana_usdc_decimals,
                )
            ),
        ]
        transaction = await self._partially_signed_transaction(
            payer=fee_payer,
            instructions=instructions,
            additional_signers=[],
        )
        if fee_payer_wallet_id is None:
            return await self._sign_and_send(
                wallet_id=self._settings.privy_treasury_wallet_id or "",
                transaction=transaction,
                reference_id=reference_id,
                from_address=str(treasury),
            )

        treasury_signed = await self._sign_transaction(
            wallet_id=self._settings.privy_treasury_wallet_id or "",
            transaction=transaction,
        )
        return await self._sign_and_send(
            wallet_id=fee_payer_wallet_id,
            transaction=treasury_signed,
            reference_id=reference_id,
            from_address=str(treasury),
        )

    async def _sign_and_send(
        self,
        *,
        wallet_id: str,
        transaction: bytes,
        reference_id: str,
        from_address: str | None = None,
    ) -> ChainTransferResult:
        if not wallet_id:
            raise IntegrationError("Privy Treasury 지갑이 설정되지 않았습니다.")
        if len(reference_id) > 64:
            raise IntegrationError("Privy reference_id must not exceed 64 characters")
        sender = from_address or await self._wallet_address(wallet_id)
        if self._settings.privy_broadcast_mode == "rpc":
            signed_transaction = await self._sign_transaction(
                wallet_id=wallet_id,
                transaction=transaction,
            )
            return await self._broadcast_signed_transaction(
                transaction=signed_transaction,
                from_address=sender,
            )
        response = await self._client.post(
            f"{self._settings.privy_api_base_url}/v1/wallets/{wallet_id}/rpc",
            json={
                "method": "signAndSendTransaction",
                "caip2": self._settings.solana_caip2,
                "sponsor": self._settings.privy_sponsor,
                "params": {
                    "transaction": base64.b64encode(transaction).decode("ascii"),
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
            from_address=sender,
            provider="PRIVY",
            sandbox=False,
        )

    async def _broadcast_signed_transaction(
        self,
        *,
        transaction: bytes,
        from_address: str,
    ) -> ChainTransferResult:
        """Send a Privy-signed Devnet transaction through the configured RPC.

        The transaction has already been signed by every required service
        wallet via Privy.  Broadcasting it through the same RPC that supplied
        the recent blockhash prevents a separate provider from rejecting a
        valid Devnet transaction with a stale or unknown blockhash.
        """

        signature = await self._rpc(
            "sendTransaction",
            [
                base64.b64encode(transaction).decode("ascii"),
                {
                    "encoding": "base64",
                    "preflightCommitment": "confirmed",
                    "maxRetries": 3,
                },
            ],
        )
        if not isinstance(signature, str) or not signature:
            raise IntegrationError("Solana RPC did not return a transaction signature")
        status = await self._confirmation_status(signature)
        return ChainTransferResult(
            signature=signature,
            status=status,
            from_address=from_address,
            provider="PRIVY",
            sandbox=False,
        )

    async def _sign_transaction(self, *, wallet_id: str, transaction: bytes) -> bytes:
        response = await self._client.post(
            f"{self._settings.privy_api_base_url}/v1/wallets/{wallet_id}/rpc",
            json={
                "method": "signTransaction",
                "params": {
                    "transaction": base64.b64encode(transaction).decode("ascii"),
                    "encoding": "base64",
                },
            },
        )
        self._raise_for_provider_error(response, "Privy signTransaction")
        payload = response.json()
        try:
            signed = payload["data"]["signed_transaction"]
            encoding = payload["data"]["encoding"]
        except (KeyError, TypeError) as exc:
            raise IntegrationError("Privy signTransaction response is incomplete") from exc
        if encoding != "base64" or not isinstance(signed, str):
            raise IntegrationError("Privy signTransaction returned an unsupported encoding")
        try:
            return base64.b64decode(signed, validate=True)
        except ValueError as exc:
            raise IntegrationError("Privy signTransaction returned invalid base64") from exc

    async def _treasury_address(self) -> str:
        configured = self.vault_address
        if not configured or configured.startswith("DEMO_"):
            raise IntegrationError("Privy Treasury 공개 주소가 설정되지 않았습니다.")
        try:
            Pubkey.from_string(configured)
        except ValueError as exc:
            raise IntegrationError("Privy Treasury 공개 주소가 올바르지 않습니다.") from exc
        actual = await self._wallet_address(self._settings.privy_treasury_wallet_id or "")
        if actual != configured:
            raise IntegrationError("설정된 Privy Treasury 주소와 지갑 주소가 일치하지 않습니다.")
        return actual

    async def _sponsor_address(self) -> str:
        configured = self._settings.privy_sponsor_wallet_address
        wallet_id = self._settings.privy_sponsor_wallet_id
        if not configured or not wallet_id:
            raise IntegrationError("Privy Sponsor 지갑이 설정되지 않았습니다.")
        try:
            Pubkey.from_string(configured)
        except ValueError as exc:
            raise IntegrationError("Privy Sponsor 공개 주소가 올바르지 않습니다.") from exc
        actual = await self._wallet_address(wallet_id)
        if actual != configured:
            raise IntegrationError("설정된 Privy Sponsor 주소와 지갑 주소가 일치하지 않습니다.")
        return actual

    def _require_issuer_wallet_id(self) -> str:
        wallet_id = self._settings.privy_rwa_issuer_wallet_id
        if not wallet_id:
            raise IntegrationError("RWA 발행용 Privy Issuer 지갑이 설정되지 않았습니다.")
        return wallet_id

    async def _platform_fee_payer(self, *, fallback: Pubkey) -> tuple[Pubkey, str | None]:
        """Return the account that pays platform-side RWA transaction fees.

        When gasless mode is enabled, issuance and the automatic RWA exchange
        use the dedicated Sponsor wallet as the message fee payer.  The issuer
        and Treasury wallets still sign only the instructions that move their
        respective assets.  Keeping the choice here prevents future Cloud Run
        orchestration from changing signing semantics at each call site.
        """

        if not self._settings.gasless_enabled:
            return fallback, None
        sponsor = Pubkey.from_string(await self._sponsor_address())
        return sponsor, self._settings.privy_sponsor_wallet_id

    async def _unsigned_transaction(self, *, payer: Pubkey, instructions: list[Any]) -> bytes:
        blockhash = Hash.from_string(await self._latest_blockhash())
        message = MessageV0.try_compile(payer, instructions, [], blockhash)
        signatures = [Signature.default()] * message.header.num_required_signatures
        return bytes(VersionedTransaction.populate(message, signatures))

    async def _partially_signed_transaction(
        self,
        *,
        payer: Pubkey,
        instructions: list[Any],
        additional_signers: list[Keypair],
    ) -> bytes:
        blockhash = Hash.from_string(await self._latest_blockhash())
        message = MessageV0.try_compile(payer, instructions, [], blockhash)
        signatures = [Signature.default()] * message.header.num_required_signatures
        message_bytes = to_bytes_versioned(message)
        for signer in additional_signers:
            try:
                index = list(message.account_keys).index(signer.pubkey())
            except ValueError as exc:
                raise IntegrationError("RWA mint signer is absent from the transaction") from exc
            if index >= message.header.num_required_signatures:
                raise IntegrationError("RWA mint signer is not a required transaction signer")
            signatures[index] = signer.sign_message(message_bytes)
        return bytes(VersionedTransaction.populate(message, signatures))

    def _token_balance_delta(
        self,
        pre_balances: object,
        post_balances: object,
        owner: str,
    ) -> int:
        def total(balances: object) -> int:
            if not isinstance(balances, list):
                return 0
            return sum(
                int((balance.get("uiTokenAmount") or {}).get("amount") or 0)
                for balance in balances
                if isinstance(balance, dict)
                and balance.get("owner") == owner
                and balance.get("mint") == self.stablecoin_mint_address
            )

        return total(post_balances) - total(pre_balances)

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
        return result

    @staticmethod
    def _raise_for_provider_error(response: httpx.Response, operation: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail: str | None = None
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    raw_detail = payload.get("message") or payload.get("error")
                    if isinstance(raw_detail, str):
                        detail = raw_detail
                    elif isinstance(raw_detail, dict):
                        nested_message = raw_detail.get("message") or raw_detail.get("code")
                        if isinstance(nested_message, str):
                            detail = nested_message
            except (ValueError, TypeError):
                pass
            suffix = f": {detail}" if detail else ""
            raise IntegrationError(
                f"{operation} failed with HTTP {response.status_code}{suffix}"
            ) from exc


def create_solana_gateway(settings: BackendSettings) -> SolanaGateway:
    """Select a direct Devnet adapter only when explicitly configured."""

    if settings.resolved_solana_mode() == "direct":
        return DirectSolanaGateway(settings)
    if settings.resolved_solana_mode() == "privy":
        return PrivySolanaGateway(settings)
    return MockSolanaGateway(settings)
