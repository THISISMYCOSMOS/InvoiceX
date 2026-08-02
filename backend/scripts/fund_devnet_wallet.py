"""Locally fund one external wallet with the configured Circle Devnet USDC.

This is deliberately a developer-only command, never an HTTP endpoint.  It
uses the configured Privy Treasury (Agent Vault) as the USDC sender and the
configured Privy Sponsor as fee payer when gasless mode is enabled.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib

from solders.pubkey import Pubkey

from invoicex_backend.config import BackendSettings
from invoicex_backend.solana import PrivySolanaGateway


def _reference_id(wallet_address: str, amount_usdc: int) -> str:
    digest = hashlib.sha256(wallet_address.encode("utf-8")).hexdigest()[:16]
    return f"devnet-fund-{digest}-{amount_usdc}"


async def run(args: argparse.Namespace) -> None:
    try:
        recipient = str(Pubkey.from_string(args.wallet))
    except ValueError as exc:
        raise SystemExit("--wallet must be a Solana public key") from exc

    settings = BackendSettings()
    if settings.resolved_solana_mode() != "privy":
        raise SystemExit("SOLANA_MODE=privy and Privy wallet settings are required")
    if args.amount_usdc <= 0:
        raise SystemExit("--amount-usdc must be positive")
    if args.amount_usdc > settings.solana_demo_transfer_amount_usdc:
        raise SystemExit(
            "--amount-usdc exceeds SOLANA_DEMO_TRANSFER_AMOUNT_USDC "
            f"({settings.solana_demo_transfer_amount_usdc})"
        )

    reference_id = _reference_id(recipient, args.amount_usdc)
    print(f"recipient={recipient}")
    print(f"amount_usdc={args.amount_usdc}")
    print(f"mint={settings.solana_usdc_mint}")
    print(f"reference_id={reference_id}")
    print(f"fee_payer={'sponsor' if settings.gasless_enabled else 'treasury'}")

    if not args.execute:
        print("dry_run=true (add --execute to submit this Devnet transfer)")
        return

    gateway = PrivySolanaGateway(settings)
    try:
        result = await gateway.fund_development_wallet(
            recipient_wallet_address=recipient,
            amount_usdc=args.amount_usdc,
            reference_id=reference_id,
        )
    finally:
        await gateway.aclose()
    print(f"signature={result.signature}")
    print(f"status={result.status.value}")
    print(f"explorer=https://explorer.solana.com/tx/{result.signature}?cluster=devnet")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wallet", required=True, help="Recipient Solana public address")
    parser.add_argument("--amount-usdc", type=int, default=1)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Submit the transfer after reviewing the dry-run output",
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
