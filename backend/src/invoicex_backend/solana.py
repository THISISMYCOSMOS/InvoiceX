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
from solders.system_program import CreateAccountWithSeedParams, create_account_with_seed
from solders.transaction import VersionedTransaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    AuthorityType,
    create_idempotent_associated_token_account,
    get_associated_token_address,
    initialize_mint2,
    mint_to_checked,
    set_authority,
    transfer_checked,
)
from spl.token.models import (
    InitializeMint2Params,
    MintToCheckedParams,
    SetAuthorityParams,
    TransferCheckedParams,
)

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import IntegrationError
from invoicex_backend.models import (
    ChainTransfer,
    ChainTransferResult,
    RwaIssuance,
    RwaPurchaseResult,
    TransactionStatus,
)

# SPL mint accounts are a fixed 82-byte layout regardless of decimals.
_MINT_ACCOUNT_SIZE = 82


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

    async def wallet_address(self, wallet_id: str) -> str:
        """Resolve the public address for a configured server wallet."""

    async def issue_invoice_rwa(self, *, invoice_id: str) -> RwaIssuance:
        """Mint exactly one non-divisible RWA token into the service escrow."""

    async def execute_rwa_purchase(
        self,
        *,
        invoice_id: str,
        rwa_mint_address: str,
        supplier_address: str,
        amount_usdc: int,
        reference_id: str,
    ) -> RwaPurchaseResult:
        """Atomically pay the supplier in USDC and move the escrowed RWA to the Vault."""

    async def verify_usdc_deposit(
        self,
        *,
        signature: str,
        from_address: str,
        to_address: str,
        amount_usdc: int,
    ) -> TransactionStatus:
        """Verify one investor-signed USDC deposit on the configured cluster."""

    async def aclose(self) -> None:
        """Release network resources."""


class MockSolanaGateway:
    """Concurrency-safe deterministic chain adapter for local and stress tests."""

    mode = "mock"

    def __init__(self, settings: BackendSettings) -> None:
        self._settings = settings
        self._results: dict[str, ChainTransferResult] = {}
        self._rwa_issuances: dict[str, RwaIssuance] = {}
        self._rwa_purchases: dict[str, RwaPurchaseResult] = {}
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

    async def wallet_address(self, wallet_id: str) -> str:
        del wallet_id
        return "So11111111111111111111111111111111111111112"

    async def issue_invoice_rwa(self, *, invoice_id: str) -> RwaIssuance:
        async with self._lock:
            existing = self._rwa_issuances.get(invoice_id)
            if existing is not None:
                return RwaIssuance(
                    mint_address=existing.mint_address,
                    escrow_address=existing.escrow_address,
                    escrow_token_account=existing.escrow_token_account,
                    signature=existing.signature,
                    status=existing.status,
                    already_issued=True,
                    provider="MOCK",
                    sandbox=True,
                )

            mint_address = str(
                Pubkey(hashlib.sha512(f"rwa-mint:{invoice_id}".encode()).digest()[:32])
            )
            escrow_token_account = str(
                Pubkey(hashlib.sha512(f"rwa-ata:{invoice_id}".encode()).digest()[:32])
            )
            signature = str(
                Signature.from_bytes(
                    hashlib.sha512(f"rwa-signature:{invoice_id}".encode()).digest()
                )
            )
            result = RwaIssuance(
                mint_address=mint_address,
                escrow_address="DEMO_RWA_ESCROW",
                escrow_token_account=escrow_token_account,
                signature=signature,
                status=TransactionStatus.CONFIRMED,
                already_issued=False,
                provider="MOCK",
                sandbox=True,
            )
            self._rwa_issuances[invoice_id] = result
            return result

    async def execute_rwa_purchase(
        self,
        *,
        invoice_id: str,
        rwa_mint_address: str,
        supplier_address: str,
        amount_usdc: int,
        reference_id: str,
    ) -> RwaPurchaseResult:
        del invoice_id
        async with self._lock:
            existing = self._rwa_purchases.get(reference_id)
            if existing is not None:
                return RwaPurchaseResult(
                    signature=existing.signature,
                    status=existing.status,
                    vault_address=existing.vault_address,
                    escrow_address=existing.escrow_address,
                    sponsor_address=existing.sponsor_address,
                    supplier_address=existing.supplier_address,
                    amount_usdc=existing.amount_usdc,
                    rwa_mint_address=existing.rwa_mint_address,
                    provider="MOCK",
                    sandbox=True,
                    already_executed=True,
                )

            digest = hashlib.sha512(f"purchase:{reference_id}".encode()).digest()
            result = RwaPurchaseResult(
                signature=str(Signature.from_bytes(digest)),
                status=TransactionStatus.CONFIRMED,
                vault_address="DEMO_AGENT_VAULT",
                escrow_address="DEMO_RWA_ESCROW",
                sponsor_address="DEMO_SPONSOR_WALLET",
                supplier_address=supplier_address,
                amount_usdc=amount_usdc,
                rwa_mint_address=rwa_mint_address,
                provider="MOCK",
                sandbox=True,
                already_executed=False,
            )
            self._rwa_purchases[reference_id] = result
            return result

    async def verify_usdc_deposit(
        self,
        *,
        signature: str,
        from_address: str,
        to_address: str,
        amount_usdc: int,
    ) -> TransactionStatus:
        del signature, from_address, to_address, amount_usdc
        return TransactionStatus.CONFIRMED

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

    async def wallet_address(self, wallet_id: str) -> str:
        return await self._wallet_address(wallet_id)

    async def issue_invoice_rwa(self, *, invoice_id: str) -> RwaIssuance:
        missing = self._settings.missing_privy_rwa_configuration()
        if missing:
            raise IntegrationError(
                "RWA 발행에 필요한 설정이 없습니다: " + ", ".join(missing)
            )
        if len(invoice_id.encode("utf-8")) > 32:
            raise IntegrationError(
                "invoice_id가 32바이트를 초과해 mint 주소를 파생할 수 없습니다."
            )

        sponsor_wallet_id = self._settings.privy_sponsor_wallet_id or ""
        rwa_wallet_id = self._settings.privy_rwa_wallet_id or ""
        sponsor_address = await self._wallet_address(sponsor_wallet_id)
        rwa_address = await self._wallet_address(rwa_wallet_id)
        try:
            sponsor_pubkey = Pubkey.from_string(sponsor_address)
            rwa_pubkey = Pubkey.from_string(rwa_address)
            mint = Pubkey.create_with_seed(sponsor_pubkey, invoice_id, TOKEN_PROGRAM_ID)
        except ValueError as exc:
            raise IntegrationError("Sponsor/RWA 지갑 주소로 mint를 파생할 수 없습니다.") from exc
        escrow_token_account = get_associated_token_address(
            rwa_pubkey, mint, TOKEN_PROGRAM_ID
        )

        if await self._account_exists(mint):
            return RwaIssuance(
                mint_address=str(mint),
                escrow_address=str(rwa_pubkey),
                escrow_token_account=str(escrow_token_account),
                signature=None,
                status=TransactionStatus.CONFIRMED,
                already_issued=True,
                provider="PRIVY",
                sandbox=False,
            )

        try:
            rent_lamports = await self._mint_rent_exempt_lamports()
            instructions = [
                create_account_with_seed(
                    CreateAccountWithSeedParams(
                        from_pubkey=sponsor_pubkey,
                        to_pubkey=mint,
                        base=sponsor_pubkey,
                        seed=invoice_id,
                        lamports=rent_lamports,
                        space=_MINT_ACCOUNT_SIZE,
                        owner=TOKEN_PROGRAM_ID,
                    )
                ),
                initialize_mint2(
                    InitializeMint2Params(
                        decimals=0,
                        program_id=TOKEN_PROGRAM_ID,
                        mint=mint,
                        mint_authority=rwa_pubkey,
                        freeze_authority=rwa_pubkey,
                    )
                ),
                create_idempotent_associated_token_account(
                    payer=sponsor_pubkey,
                    owner=rwa_pubkey,
                    mint=mint,
                    token_program_id=TOKEN_PROGRAM_ID,
                ),
                mint_to_checked(
                    MintToCheckedParams(
                        program_id=TOKEN_PROGRAM_ID,
                        mint=mint,
                        dest=escrow_token_account,
                        mint_authority=rwa_pubkey,
                        amount=1,
                        decimals=0,
                        signers=[],
                    )
                ),
                set_authority(
                    SetAuthorityParams(
                        program_id=TOKEN_PROGRAM_ID,
                        account=mint,
                        authority=AuthorityType.MINT_TOKENS,
                        current_authority=rwa_pubkey,
                        signers=[],
                        new_authority=None,
                    )
                ),
            ]
            recent_blockhash = Hash.from_string(await self._latest_blockhash())
            message = MessageV0.try_compile(
                payer=sponsor_pubkey,
                instructions=instructions,
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash,
            )
            unsigned = VersionedTransaction.populate(
                message,
                [Signature.default()] * message.header.num_required_signatures,
            )
            encoded_transaction = base64.b64encode(bytes(unsigned)).decode("ascii")

            signed_by_rwa = await self._sign_with_wallet(rwa_wallet_id, encoded_transaction)
            signed_by_sponsor = await self._sign_with_wallet(
                sponsor_wallet_id, signed_by_rwa
            )
            signature = await self._send_transaction(signed_by_sponsor)
        except httpx.HTTPError as exc:
            raise IntegrationError("Privy 또는 Solana 네트워크 요청이 실패했습니다.") from exc
        except ValueError as exc:
            raise IntegrationError(
                "Privy/Solana가 잘못된 데이터를 반환했거나 주소가 올바르지 않습니다."
            ) from exc

        status = await self._confirmation_status(signature)
        return RwaIssuance(
            mint_address=str(mint),
            escrow_address=str(rwa_pubkey),
            escrow_token_account=str(escrow_token_account),
            signature=signature,
            status=status,
            already_issued=False,
            provider="PRIVY",
            sandbox=False,
        )

    async def execute_rwa_purchase(
        self,
        *,
        invoice_id: str,
        rwa_mint_address: str,
        supplier_address: str,
        amount_usdc: int,
        reference_id: str,
    ) -> RwaPurchaseResult:
        del invoice_id
        missing = [
            *self._settings.missing_privy_rwa_configuration(),
            *self._settings._missing_configuration(
                {"PRIVY_TREASURY_WALLET_ID": self._settings.privy_treasury_wallet_id}
            ),
        ]
        if missing:
            raise IntegrationError(
                "자동 매수에 필요한 설정이 없습니다: " + ", ".join(missing)
            )

        treasury_wallet_id = self._settings.privy_treasury_wallet_id or ""
        rwa_wallet_id = self._settings.privy_rwa_wallet_id or ""
        sponsor_wallet_id = self._settings.privy_sponsor_wallet_id or ""
        vault_address = await self._wallet_address(treasury_wallet_id)
        escrow_address = await self._wallet_address(rwa_wallet_id)
        sponsor_address = await self._wallet_address(sponsor_wallet_id)

        try:
            vault_pubkey = Pubkey.from_string(vault_address)
            escrow_pubkey = Pubkey.from_string(escrow_address)
            sponsor_pubkey = Pubkey.from_string(sponsor_address)
            supplier_pubkey = Pubkey.from_string(supplier_address)
            rwa_mint_pubkey = Pubkey.from_string(rwa_mint_address)
            usdc_mint_pubkey = Pubkey.from_string(self._settings.solana_usdc_mint)
        except ValueError as exc:
            raise IntegrationError(
                "자동 매수에 필요한 Solana 주소가 올바르지 않습니다."
            ) from exc

        vault_rwa_ata = get_associated_token_address(
            vault_pubkey, rwa_mint_pubkey, TOKEN_PROGRAM_ID
        )
        if await self._rwa_already_at_vault(vault_rwa_ata):
            return RwaPurchaseResult(
                signature="",
                status=TransactionStatus.CONFIRMED,
                vault_address=vault_address,
                escrow_address=escrow_address,
                sponsor_address=sponsor_address,
                supplier_address=supplier_address,
                amount_usdc=amount_usdc,
                rwa_mint_address=rwa_mint_address,
                provider="PRIVY",
                sandbox=False,
                already_executed=True,
            )

        try:
            vault_usdc_ata = get_associated_token_address(
                vault_pubkey, usdc_mint_pubkey, TOKEN_PROGRAM_ID
            )
            supplier_usdc_ata = get_associated_token_address(
                supplier_pubkey, usdc_mint_pubkey, TOKEN_PROGRAM_ID
            )
            escrow_rwa_ata = get_associated_token_address(
                escrow_pubkey, rwa_mint_pubkey, TOKEN_PROGRAM_ID
            )
            usdc_decimals = self._settings.solana_usdc_decimals
            instructions = [
                create_idempotent_associated_token_account(
                    payer=sponsor_pubkey,
                    owner=supplier_pubkey,
                    mint=usdc_mint_pubkey,
                    token_program_id=TOKEN_PROGRAM_ID,
                ),
                transfer_checked(
                    TransferCheckedParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=vault_usdc_ata,
                        mint=usdc_mint_pubkey,
                        dest=supplier_usdc_ata,
                        owner=vault_pubkey,
                        amount=amount_usdc * (10**usdc_decimals),
                        decimals=usdc_decimals,
                    )
                ),
                create_idempotent_associated_token_account(
                    payer=sponsor_pubkey,
                    owner=vault_pubkey,
                    mint=rwa_mint_pubkey,
                    token_program_id=TOKEN_PROGRAM_ID,
                ),
                transfer_checked(
                    TransferCheckedParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=escrow_rwa_ata,
                        mint=rwa_mint_pubkey,
                        dest=vault_rwa_ata,
                        owner=escrow_pubkey,
                        amount=1,
                        decimals=0,
                    )
                ),
            ]

            expected_signers = len({sponsor_pubkey, vault_pubkey, escrow_pubkey})
            recent_blockhash = Hash.from_string(await self._latest_blockhash())
            message = MessageV0.try_compile(
                payer=sponsor_pubkey,
                instructions=instructions,
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash,
            )
            if message.header.num_required_signatures != expected_signers:
                raise IntegrationError(
                    "자동 매수 트랜잭션의 서명자 수가 예상과 다릅니다. "
                    "Vault/Escrow/Sponsor 지갑 설정을 확인하세요."
                )

            unsigned = VersionedTransaction.populate(
                message,
                [Signature.default()] * message.header.num_required_signatures,
            )
            encoded_transaction = base64.b64encode(bytes(unsigned)).decode("ascii")
            idempotency_key = f"invoicex:{reference_id}"

            signed = await self._sign_with_wallet(
                treasury_wallet_id, encoded_transaction, idempotency_key=idempotency_key
            )
            if rwa_wallet_id != treasury_wallet_id:
                signed = await self._sign_with_wallet(
                    rwa_wallet_id, signed, idempotency_key=idempotency_key
                )
            signed = await self._sign_with_wallet(
                sponsor_wallet_id, signed, idempotency_key=idempotency_key
            )
            signature = await self._send_transaction(signed)
        except httpx.HTTPError as exc:
            raise IntegrationError("Privy 또는 Solana 네트워크 요청이 실패했습니다.") from exc
        except ValueError as exc:
            raise IntegrationError(
                "Privy/Solana가 잘못된 데이터를 반환했거나 주소가 올바르지 않습니다."
            ) from exc

        status = await self._confirmation_status(signature)
        return RwaPurchaseResult(
            signature=signature,
            status=status,
            vault_address=vault_address,
            escrow_address=escrow_address,
            sponsor_address=sponsor_address,
            supplier_address=supplier_address,
            amount_usdc=amount_usdc,
            rwa_mint_address=rwa_mint_address,
            provider="PRIVY",
            sandbox=False,
            already_executed=False,
        )

    async def verify_usdc_deposit(
        self,
        *,
        signature: str,
        from_address: str,
        to_address: str,
        amount_usdc: int,
    ) -> TransactionStatus:
        try:
            Signature.from_string(signature)
            Pubkey.from_string(from_address)
            Pubkey.from_string(to_address)
        except ValueError as exc:
            raise IntegrationError("Deposit contains an invalid Solana identifier") from exc

        status = await self._confirmation_status(signature)
        if status is not TransactionStatus.CONFIRMED:
            return status

        transaction = await self._rpc(
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
        try:
            meta = transaction["meta"]
            message = transaction["transaction"]["message"]
            if not isinstance(meta, dict) or meta.get("err") is not None:
                raise IntegrationError("Deposit transaction failed on-chain")
            if not isinstance(message, dict):
                raise TypeError

            account_keys = message.get("accountKeys")
            if not isinstance(account_keys, list) or not any(
                isinstance(account, dict)
                and account.get("pubkey") == from_address
                and account.get("signer") is True
                for account in account_keys
            ):
                raise IntegrationError("Investor wallet did not sign the deposit")

            pre = self._token_balances_by_owner(meta.get("preTokenBalances"))
            post = self._token_balances_by_owner(meta.get("postTokenBalances"))
            expected_raw = amount_usdc * (10**self._settings.solana_usdc_decimals)
            investor_delta = pre.get(from_address, 0) - post.get(from_address, 0)
            treasury_delta = post.get(to_address, 0) - pre.get(to_address, 0)
            if investor_delta != expected_raw or treasury_delta != expected_raw:
                raise IntegrationError(
                    "Deposit amount, mint, or destination did not match preparation"
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrationError("Solana deposit transaction data was invalid") from exc
        return TransactionStatus.CONFIRMED

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
        result = await self._rpc_result(method, params)
        if not isinstance(result, dict):
            raise IntegrationError(f"Solana RPC {method} returned an invalid result")
        return result

    async def _rpc_result(self, method: str, params: list[object]) -> object:
        """Resolve a Solana RPC call without assuming the ``result`` shape.

        Most JSON-RPC methods return a ``{"context": ..., "value": ...}``
        object, which ``_rpc`` enforces. A few (``getMinimumBalanceForRent
        Exemption`` returns a plain integer, ``sendTransaction`` returns a
        plain signature string) do not, so callers that need those use this
        directly.
        """

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
        return payload.get("result")

    async def _account_exists(self, address: Pubkey) -> bool:
        result = await self._rpc(
            "getAccountInfo",
            [str(address), {"encoding": "base64", "commitment": "confirmed"}],
        )
        return result.get("value") is not None

    async def _rwa_already_at_vault(self, vault_rwa_ata: Pubkey) -> bool:
        """Check on-chain whether the Vault already holds the escrowed RWA.

        A missing token account is reported by the RPC as a JSON-RPC error
        (``_rpc_result`` raises ``IntegrationError`` in that case); that means
        the purchase has not happened yet, not that the check failed, so it
        is treated as "not yet executed" rather than propagated.
        """

        try:
            result = await self._rpc_result(
                "getTokenAccountBalance",
                [str(vault_rwa_ata), {"commitment": "confirmed"}],
            )
        except IntegrationError:
            return False
        if not isinstance(result, dict):
            return False
        value = result.get("value")
        if not isinstance(value, dict):
            return False
        amount = value.get("amount")
        if not isinstance(amount, str):
            return False
        try:
            return int(amount) >= 1
        except ValueError:
            return False

    async def _mint_rent_exempt_lamports(self) -> int:
        result = await self._rpc_result(
            "getMinimumBalanceForRentExemption", [_MINT_ACCOUNT_SIZE]
        )
        if not isinstance(result, int):
            raise IntegrationError(
                "Solana RPC getMinimumBalanceForRentExemption returned an invalid result"
            )
        return result

    async def _sign_with_wallet(
        self,
        wallet_id: str,
        encoded_transaction: str,
        *,
        idempotency_key: str | None = None,
    ) -> str:
        headers = (
            {"privy-idempotency-key": idempotency_key}
            if idempotency_key is not None
            else None
        )
        response = await self._client.post(
            f"{self._settings.privy_api_base_url}/v1/wallets/{wallet_id}/rpc",
            headers=headers,
            json={
                "method": "signTransaction",
                "params": {
                    "transaction": encoded_transaction,
                    "encoding": "base64",
                },
            },
        )
        self._raise_for_provider_error(response, "Privy signTransaction")
        payload = response.json()
        try:
            signed_transaction = payload["data"]["signed_transaction"]
        except (KeyError, TypeError) as exc:
            raise IntegrationError(
                "Privy signTransaction response did not contain a signed transaction"
            ) from exc
        if not isinstance(signed_transaction, str) or not signed_transaction:
            raise IntegrationError("Privy signTransaction returned an empty transaction")
        return signed_transaction

    async def _send_transaction(self, encoded_transaction: str) -> str:
        result = await self._rpc_result(
            "sendTransaction",
            [
                encoded_transaction,
                {
                    "encoding": "base64",
                    "skipPreflight": False,
                    "preflightCommitment": "confirmed",
                },
            ],
        )
        if not isinstance(result, str) or not result:
            raise IntegrationError("Solana RPC sendTransaction did not return a signature")
        return result

    def _token_balances_by_owner(self, value: object) -> dict[str, int]:
        balances: dict[str, int] = {}
        if not isinstance(value, list):
            return balances
        for entry in value:
            if not isinstance(entry, dict):
                continue
            if entry.get("mint") != self._settings.solana_usdc_mint:
                continue
            owner = entry.get("owner")
            token_amount = entry.get("uiTokenAmount")
            if not isinstance(owner, str) or not isinstance(token_amount, dict):
                continue
            amount = token_amount.get("amount")
            if not isinstance(amount, str):
                continue
            balances[owner] = balances.get(owner, 0) + int(amount)
        return balances

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
