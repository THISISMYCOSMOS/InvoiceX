# InvoiceX

## Solana Devnet wallet runbook

팀원 또는 AI 작업자가 Devnet SOL·USDC 준비, MetaMask 역할별 계정 연결,
투자자 예치와 온체인 검증을 재현할 때는
[`docs/SOLANA_DEVNET_WALLET_RUNBOOK.md`](docs/SOLANA_DEVNET_WALLET_RUNBOOK.md)를
먼저 읽어야 합니다. 실제/목업 경계, 공개 데모 주소, 중단 조건과 확인된 오류
대응 절차를 이 문서에 모았습니다.

## Local Gemini document analysis

The frontend already sends uploaded invoice documents to `POST /api/v1/invoices`.
Run the backend and configure Gemini there; never expose `GEMINI_API_KEY` through a
`VITE_` frontend variable.

> **Keep the backend configuration in one file.** Settings are read from both
> `.env` at the repository root and `backend/.env`, and the two are merged with
> `backend/.env` winning on shared keys. A key left empty in `backend/.env` therefore
> shadows a real value in the root `.env`, which drops the demo to mock mode with no
> error. Pick one location and delete the other.

1. Copy `backend/.env.example` to `backend/.env` and set `GEMINI_API_KEY`.
2. Set `AGENT_MODE=real` in `backend/.env` to fail fast when the key is unavailable.
3. Start the API with `cd backend && uv sync --all-groups && uv run uvicorn invoicex_backend.main:app --reload --port 8000`.
4. Copy `frontend/.env.example` to `frontend/.env.local`, then start the frontend from `frontend` with `npm run dev`.

`VITE_USE_MOCK_API=false` makes the frontend use the backend API. With no Gemini key,
`AGENT_MODE=auto` deliberately uses the backend's mock analyzer instead.

For the Privy-backed Devnet RWA demo, follow the **Real Devnet RWA demo**
section in `backend/README.md`. Keep `PRIVY_APP_SECRET` only in
`backend/.env` locally or Secret Manager on Cloud Run; never put it in a Vite
environment file. The older direct keypair tooling is for isolated local tests
only.
