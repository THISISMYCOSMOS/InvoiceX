# InvoiceX

## Local Gemini document analysis

The frontend already sends uploaded invoice documents to `POST /api/v1/invoices`.
Run the backend and configure Gemini there; never expose `GEMINI_API_KEY` through a
`VITE_` frontend variable.

1. Copy `backend/.env.example` to `backend/.env` and set `GEMINI_API_KEY`.
2. Set `AGENT_MODE=real` in `backend/.env` to fail fast when the key is unavailable.
3. Start the API with `cd backend && uv sync --all-groups && uv run uvicorn invoicex_backend.main:app --reload --port 8000`.
4. Copy `frontend/.env.example` to `frontend/.env.local`, then start the frontend from `frontend` with `npm run dev`.

`VITE_USE_MOCK_API=false` makes the frontend use the backend API. With no Gemini key,
`AGENT_MODE=auto` deliberately uses the backend's mock analyzer instead.
