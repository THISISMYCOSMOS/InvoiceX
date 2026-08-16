# InvoiceX Backend

FastAPI implementation of `docs/FRONTEND_API_CONTRACT_DRAFT.md`.

## Run

The repository's existing `agent/` package must be present beside `backend/`.

```powershell
cd backend
Copy-Item .env.example .env
uv sync --all-groups
uv run uvicorn invoicex_backend.main:app --reload --port 8000
```

- Swagger UI: `http://localhost:8000/api/docs`
- OpenAPI JSON: `http://localhost:8000/api/docs-json`
- API base URL: `http://localhost:8000/api/v1`

`AGENT_MODE=auto` uses the real Gemini agents only when `GEMINI_API_KEY` is
configured. `SOLANA_MODE=auto` uses the direct Devnet adapter only when every
service-wallet and demo-stablecoin value is configured; otherwise it uses mock
mode. Explicit `real`, `direct`, or `privy` modes fail during startup when
their required configuration is missing; provider failures never fall back to
mock execution.

## Privy user authentication

Investor APIs can enforce both the authenticated Privy session and embedded-wallet
ownership. In Privy Dashboard, enable **Return user data in an identity token**, then
configure the backend only:

```dotenv
AUTH_MODE=privy
PRIVY_APP_ID=
PRIVY_JWKS_URL=https://auth.privy.io/api/v1/apps/<PRIVY_APP_ID>/jwks.json
```

The frontend sends the access token as `Authorization: Bearer ...` and the identity
token as `privy-id-token`. The API verifies both ES256 signatures through Privy's
cached JWKS endpoint, as well as issuer, audience,
expiry, and matching Privy user IDs. An investor request is authorized only when its
`ownerWalletAddress` appears as a Privy-managed Solana wallet in the signed identity
token. `AUTH_MODE=disabled` is limited to local mock tests.

## Real Devnet RWA demo

The Devnet demo issues one indivisible SPL token per invoice. The platform
service wallet controls the mint and escrow; the Agent Vault service wallet
holds only the investor's deposited demo stablecoin. Neither private key is
sent to the frontend.

1. Create two service keypairs locally. Do **not** commit the printed secrets.

   ```bash
   uv run python scripts/devnet_stablecoin.py generate-keypair --label SOLANA_PLATFORM
   uv run python scripts/devnet_stablecoin.py generate-keypair --label SOLANA_AGENT_VAULT
   ```

2. Put the two `*_KEYPAIR` values in `SOLANA_PLATFORM_KEYPAIR` and
   `SOLANA_AGENT_VAULT_KEYPAIR` in `backend/.env`, then give both public keys
   Devnet SOL using a trusted faucet or the local CLI:

   ```bash
   uv run python scripts/devnet_stablecoin.py airdrop-sol --wallet <platform-public-key>
   uv run python scripts/devnet_stablecoin.py airdrop-sol --wallet <agent-vault-public-key>
   ```

3. Create the platform test stablecoin, paste the printed mint into
   `DEMO_STABLECOIN_MINT`, and set `SOLANA_MODE=direct`.

   ```bash
   uv run python scripts/devnet_stablecoin.py create-mint
   ```

4. Fund the investor's connected Devnet wallet from the developer machine;
   there is intentionally no public funding API.

   ```bash
   uv run python scripts/devnet_stablecoin.py mint --wallet <investor-wallet> --amount-usdc 50000
   ```

5. Start the backend and frontend with `VITE_USE_MOCK_API=false`. The investor
   signs the policy and Vault deposit in their browser wallet. A qualifying RWA
   then transfers atomically: Agent Vault stablecoin to the supplier and the
   escrowed RWA to Agent Vault.

## Verify

```powershell
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/stress_api.py --iterations 500 --concurrency 25
```

The stress runner uses deterministic Agent and Solana adapters, so it does not
consume Gemini quota or submit on-chain transactions.
