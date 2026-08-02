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
configured. For the shared Devnet flow, set `SOLANA_MODE=privy` explicitly so
the server fails during startup when Privy configuration is missing rather than
falling back to mock execution. The older `direct` adapter remains only for
isolated local tests with developer-managed keypairs.

## Real Devnet RWA demo

The Devnet demo issues one indivisible SPL token per invoice. Privy manages
three service wallets: Treasury / Agent Vault holds the investor's deposited
USDC, Issuer / Escrow mints and holds the RWA, and Sponsor pays Devnet SOL
fees. External supplier and investor wallets remain browser wallets; neither
their private keys nor Privy secrets are sent to the frontend.

1. Copy `.env.example` to `backend/.env` and set the Privy App ID / Secret,
   Treasury, Issuer, and Sponsor wallet values. Keep the App Secret in Secret
   Manager for Cloud Run; do not share it through Git or the frontend.

2. Fund the Sponsor wallet with Devnet SOL and fund the investor's external
   wallet with Circle Devnet USDC using the Mint configured in `SOLANA_USDC_MINT`.
   If the Circle faucet is rate-limited, a developer can fund **up to the demo
   limit** from the existing Agent Vault using the local-only command below.
   Review the dry run first; `--execute` is required to broadcast anything.

   ```powershell
   uv run python scripts/fund_devnet_wallet.py --wallet <INVESTOR_PUBLIC_ADDRESS> --amount-usdc 1
   uv run python scripts/fund_devnet_wallet.py --wallet <INVESTOR_PUBLIC_ADDRESS> --amount-usdc 1 --execute
   ```

   The Treasury authorizes the USDC transfer and Sponsor pays the Devnet SOL
   fee. This is deliberately not exposed as an HTTP API.

3. Start the backend and frontend with `VITE_USE_MOCK_API=false`. The investor
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
