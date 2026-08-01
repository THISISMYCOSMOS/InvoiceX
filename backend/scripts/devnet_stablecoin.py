"""Local-only Devnet bootstrap and funding tool for the InvoiceX demo asset.

This script never exposes a public funding endpoint.  Run it only from a
developer machine with the service-wallet private key stored in ``backend/.env``.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.system_program import CreateAccountParams, create_account
from solders.transaction import VersionedTransaction
from spl.token.constants import MINT_LEN, TOKEN_PROGRAM_ID
from spl.token.instructions import (
    create_idempotent_associated_token_account,
    get_associated_token_address,
    initialize_mint,
    mint_to_checked,
)
from spl.token.models import InitializeMintParams, MintToCheckedParams

from invoicex_backend.config import BackendSettings


class DevnetStablecoinCli:
    def __init__(self, settings: BackendSettings) -> None:
        self._settings = settings
        try:
            self._platform = Keypair.from_base58_string(settings.solana_platform_keypair or "")
        except ValueError as exc:
            raise SystemExit("SOLANA_PLATFORM_KEYPAIR must be set in backend/.env") from exc
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def create_mint(self) -> str:
        mint = Keypair()
        rent = await self._rpc("getMinimumBalanceForRentExemption", [MINT_LEN])
        if not isinstance(rent, int):
            raise SystemExit("Solana RPC did not return the mint rent exemption")
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
                    decimals=self._settings.solana_usdc_decimals,
                    program_id=TOKEN_PROGRAM_ID,
                    mint=mint.pubkey(),
                    mint_authority=self._platform.pubkey(),
                )
            ),
        ]
        signature = await self._send(instructions, [self._platform, mint])
        await self._confirm(signature)
        return str(mint.pubkey())

    async def mint_to(self, destination_wallet: str, amount_usdc: str) -> str:
        try:
            destination = Pubkey.from_string(destination_wallet)
        except ValueError as exc:
            raise SystemExit("--wallet must be a Solana public key") from exc
        try:
            amount = Decimal(amount_usdc)
        except InvalidOperation as exc:
            raise SystemExit("--amount-usdc must be a decimal number") from exc
        if amount <= 0:
            raise SystemExit("--amount-usdc must be positive")
        try:
            mint = Pubkey.from_string(self._settings.demo_stablecoin_mint or "")
        except ValueError as exc:
            raise SystemExit("DEMO_STABLECOIN_MINT must be set in backend/.env") from exc
        raw_amount = int(amount * Decimal(10) ** self._settings.solana_usdc_decimals)
        if Decimal(raw_amount) != amount * Decimal(10) ** self._settings.solana_usdc_decimals:
            raise SystemExit("--amount-usdc has too many decimal places")
        destination_token = get_associated_token_address(destination, mint)
        instructions = [
            create_idempotent_associated_token_account(
                payer=self._platform.pubkey(),
                owner=destination,
                mint=mint,
            ),
            mint_to_checked(
                MintToCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    mint=mint,
                    dest=destination_token,
                    mint_authority=self._platform.pubkey(),
                    amount=raw_amount,
                    decimals=self._settings.solana_usdc_decimals,
                )
            ),
        ]
        signature = await self._send(instructions, [self._platform])
        await self._confirm(signature)
        return signature

    async def airdrop_sol(self, destination_wallet: str, sol: int) -> str:
        try:
            destination = Pubkey.from_string(destination_wallet)
        except ValueError as exc:
            raise SystemExit("--wallet must be a Solana public key") from exc
        if sol <= 0:
            raise SystemExit("--sol must be positive")
        signature = await self._rpc(
            "requestAirdrop",
            [str(destination), sol * 1_000_000_000, {"commitment": "confirmed"}],
        )
        if not isinstance(signature, str):
            raise SystemExit("Solana devnet faucet did not return a signature")
        await self._confirm(signature)
        return signature

    async def _send(self, instructions: list[Any], signers: list[Keypair]) -> str:
        blockhash = Hash.from_string(await self._latest_blockhash())
        message = MessageV0.try_compile(self._platform.pubkey(), instructions, [], blockhash)
        transaction = VersionedTransaction(message, signers)
        signature = await self._rpc(
            "sendTransaction",
            [
                base64.b64encode(bytes(transaction)).decode("ascii"),
                {"encoding": "base64", "preflightCommitment": "confirmed"},
            ],
        )
        if not isinstance(signature, str) or not signature:
            raise SystemExit("Solana RPC did not return a transaction signature")
        return signature

    async def _latest_blockhash(self) -> str:
        payload = await self._rpc("getLatestBlockhash", [{"commitment": "confirmed"}])
        try:
            return str(payload["value"]["blockhash"])
        except (KeyError, TypeError) as exc:
            raise SystemExit("Solana RPC did not return a recent blockhash") from exc

    async def _confirm(self, signature: str) -> None:
        for _ in range(30):
            payload = await self._rpc(
                "getSignatureStatuses",
                [[signature], {"searchTransactionHistory": True}],
            )
            values = payload.get("value") if isinstance(payload, dict) else None
            status = values[0] if isinstance(values, list) and values else None
            if isinstance(status, dict):
                if status.get("err") is not None:
                    raise SystemExit("Devnet transaction was rejected on-chain")
                if status.get("confirmationStatus") in {"confirmed", "finalized"}:
                    return
            await asyncio.sleep(1)
        raise SystemExit("Timed out waiting for Devnet transaction confirmation")

    async def _rpc(self, method: str, params: list[object]) -> Any:
        response = await self._client.post(
            self._settings.solana_rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            headers={"content-type": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error") is not None:
            raise SystemExit(f"Solana RPC {method} returned an error")
        return payload.get("result")


async def run(args: argparse.Namespace) -> None:
    if args.command == "generate-keypair":
        pair = Keypair()
        print(f"{args.label}_PUBLIC_KEY={pair.pubkey()}")
        print(f"{args.label}_KEYPAIR={pair}")
        return

    # Mint creation is the bootstrap step before DEMO_STABLECOIN_MINT exists.
    # Force auto mode so an eventual SOLANA_MODE=direct in .env does not block it.
    settings = BackendSettings(SOLANA_MODE="auto")
    cli = DevnetStablecoinCli(settings)
    try:
        if args.command == "create-mint":
            mint = await cli.create_mint()
            print(f"DEMO_STABLECOIN_MINT={mint}")
        elif args.command == "mint":
            signature = await cli.mint_to(args.wallet, args.amount_usdc)
            print(f"signature={signature}")
        elif args.command == "airdrop-sol":
            signature = await cli.airdrop_sol(args.wallet, args.sol)
            print(f"signature={signature}")
    finally:
        await cli.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    keypair = commands.add_parser("generate-keypair")
    keypair.add_argument("--label", default="SOLANA_SERVICE")
    commands.add_parser("create-mint")
    mint = commands.add_parser("mint")
    mint.add_argument("--wallet", required=True)
    mint.add_argument("--amount-usdc", required=True)
    airdrop = commands.add_parser("airdrop-sol")
    airdrop.add_argument("--wallet", required=True)
    airdrop.add_argument("--sol", type=int, default=2)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
