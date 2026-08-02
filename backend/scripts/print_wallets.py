"""Print the public addresses and Devnet balances of the configured Privy wallets.

This script never prints secret values (Privy app secret, wallet private
keys). It only resolves and displays public Solana addresses plus their
Devnet SOL and USDC balances via the public Solana RPC.

Usage::

    uv run python scripts/print_wallets.py
"""

from __future__ import annotations

import asyncio

import httpx

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import IntegrationError
from invoicex_backend.solana import PrivySolanaGateway

LAMPORTS_PER_SOL = 1_000_000_000

WALLET_ROLES: tuple[tuple[str, str], ...] = (
    ("Treasury / Agent Vault", "privy_treasury_wallet_id"),
    ("RWA Issuer + Escrow", "privy_rwa_wallet_id"),
    ("Gas Sponsor", "privy_sponsor_wallet_id"),
)


async def _sol_balance(client: httpx.AsyncClient, rpc_url: str, address: str) -> float:
    response = await client.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [address, {"commitment": "confirmed"}],
        },
    )
    response.raise_for_status()
    payload = response.json()
    lamports = payload["result"]["value"]
    return lamports / LAMPORTS_PER_SOL


async def _usdc_balance(
    client: httpx.AsyncClient,
    rpc_url: str,
    address: str,
    mint: str,
) -> float:
    response = await client.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                address,
                {"mint": mint},
                {"encoding": "jsonParsed", "commitment": "confirmed"},
            ],
        },
    )
    response.raise_for_status()
    payload = response.json()
    accounts = payload["result"]["value"]
    total = 0.0
    for account in accounts:
        token_amount = account["account"]["data"]["parsed"]["info"]["tokenAmount"]
        total += float(token_amount["uiAmountString"])
    return total


async def main() -> None:
    settings = BackendSettings()
    if settings.resolved_solana_mode() != "privy":
        print(
            "SOLANA_MODE이 mock으로 해석됩니다 (Privy 설정이 없거나 SOLANA_MODE=mock). "
            "지갑 조회를 건너뜁니다."
        )
        return

    gateway = PrivySolanaGateway(settings)
    rpc_client = httpx.AsyncClient(timeout=httpx.Timeout(30))
    rows: list[tuple[str, str, float | None, float | None]] = []
    try:
        for role, attribute in WALLET_ROLES:
            wallet_id = getattr(settings, attribute)
            if not wallet_id:
                rows.append((role, "(설정되지 않음)", None, None))
                continue
            try:
                address = await gateway.wallet_address(wallet_id)
            except (IntegrationError, httpx.HTTPError) as exc:
                rows.append((role, f"(조회 실패: {exc})", None, None))
                continue
            try:
                sol_balance = await _sol_balance(
                    rpc_client, settings.solana_rpc_url, address
                )
                usdc_balance = await _usdc_balance(
                    rpc_client,
                    settings.solana_rpc_url,
                    address,
                    settings.solana_usdc_mint,
                )
            except httpx.HTTPError as exc:
                rows.append((role, address, None, None))
                print(f"  경고: {role} 잔액 조회 실패: {exc}")
                continue
            rows.append((role, address, sol_balance, usdc_balance))
    finally:
        await gateway.aclose()
        await rpc_client.aclose()

    header = f"{'역할':<26}{'공개 주소':<48}{'SOL':>14}{'USDC':>14}"
    print(header)
    print("-" * len(header))
    for role, address, sol_balance, usdc_balance in rows:
        sol_display = "-" if sol_balance is None else f"{sol_balance:.6f}"
        usdc_display = "-" if usdc_balance is None else f"{usdc_balance:.6f}"
        print(f"{role:<26}{address:<48}{sol_display:>14}{usdc_display:>14}")


if __name__ == "__main__":
    asyncio.run(main())
