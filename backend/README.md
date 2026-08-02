# InvoiceX Backend

FastAPI implementation of `docs/FRONTEND_API_CONTRACT_DRAFT.md`.

## Firebase architecture

The backend now follows a Firebase-first persistence plan with Firebase Admin
SDK:

- Cloud Firestore persists invoice aggregates, Document Agent analyses, and
  buyer verifications.
- Investor Vault runtime state (connected investor wallet, Treasury address,
  deposit preparations, confirmed deposits, already-applied Solana signatures,
  logical Vault balance, funding reservations, and the deposit ID sequence) is
  written as a single Firestore document, `{prefix}_runtime/investor`, so that
  balance, reservation, and replay-protection updates commit atomically.
- Cloud Storage for Firebase stores uploaded PDFs and images under
  `invoices/{invoiceId}/{documentId}`.
- API responses expose a stable backend `/uploads/{invoiceId}/{documentId}`
  URL; the backend reads the private object instead of persisting expiring
  signed URLs.
- Application Default Credentials authenticate the trusted backend.
- Firestore and Storage Security Rules deny direct client access. The Admin SDK
  uses IAM and does not rely on client Security Rules.
- `FIREBASE_MODE=auto` selects Firebase when `FIREBASE_PROJECT_ID` (or
  `GOOGLE_CLOUD_PROJECT`) is present; otherwise it uses local memory and disk.

Firebase Authentication is reserved for the account/role API slice. The current
frontend contract has no user or role claims, so this change does not invent an
incompatible authentication contract.

The current workflow cache, locks, and readable IDs are process-local. Run one
API worker/replica for the MVP; move state transitions and ID allocation into
Firestore transactions before horizontal scaling.

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

For Firebase, set at least `FIREBASE_PROJECT_ID`. The default bucket is derived
as `{projectId}.firebasestorage.app`; override it with
`FIREBASE_STORAGE_BUCKET` when the Firebase console shows a different bucket.
In local shells, set `GOOGLE_APPLICATION_CREDENTIALS` to a service-account JSON
file outside the repository. Managed Firebase/Google runtimes should use their
attached identity and require no key file.
Cloud Storage for Firebase requires the Firebase Blaze plan, so enable billing
before the first production upload.

`AGENT_MODE=auto` uses the real Gemini agents only when `GEMINI_API_KEY` is
configured. `SOLANA_MODE=auto` uses Privy/Solana Devnet only when every wallet
and provider value is configured. Explicit `real` or `privy` modes fail during
startup when required configuration is missing; provider failures never fall
back to mock execution.

## Firebase emulators

From the repository root:

```powershell
firebase emulators:start --only firestore,storage
```

Then set `FIREBASE_PROJECT_ID`, `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080`, and
`FIREBASE_STORAGE_EMULATOR_HOST=127.0.0.1:9199`. Emulator host values must not
include `http://`.

## Verify

```powershell
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/stress_api.py --iterations 500 --concurrency 25
```

The stress runner uses deterministic Agent and Solana adapters, so it does not
consume Gemini quota or submit on-chain transactions.
