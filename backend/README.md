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
configured. `SOLANA_MODE=auto` uses Privy/Solana Devnet only when every wallet
and provider value is configured. Explicit `real` or `privy` modes fail during
startup when required configuration is missing; provider failures never fall
back to mock execution.

## Verify

```powershell
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/stress_api.py --iterations 500 --concurrency 25
```

The stress runner uses deterministic Agent and Solana adapters, so it does not
consume Gemini quota or submit on-chain transactions.
