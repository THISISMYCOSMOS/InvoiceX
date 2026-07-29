# InvoiceX Frontend Foundation Design

## Purpose and scope

Build the pre-design frontend foundation for the InvoiceX hackathon MVP on the existing `feat-frontend` branch. The foundation provides role-based screens, a complete replayable demo state flow, document-upload and analysis-review shells, and an API boundary that can use either an in-memory mock or the backend's `/api/v1` endpoints.

It does not implement authentication, Gemini calls, risk scoring, AP2 verification, wallet signing, Solana transfers, or a final visual design system. Those remain backend, agent, and future-design responsibilities.

## Repository and contract findings

- The checkout is `feat-frontend`; its only product file is `frontend/.gitkeep`.
- No frontend package, backend implementation, OpenAPI specification, or DTO definitions are currently committed.
- `docs/` is untracked in this checkout. The supplied source documents will not be modified or added to commits.
- The supplied API contract supersedes the older example routes in the frontend request. The frontend will target `/api/v1` through an adapter.
- The response bodies and multipart field names have not yet been specified in committed code. They are isolated inside the real API adapter so backend integration changes do not leak into components or domain types.

## Chosen approach

Create an isolated Vite + React + TypeScript application in `frontend/`, using React Router for routes, TanStack Query for server state, and Vitest plus Testing Library for tests.

This is preferred over placing frontend files in the repository root because it preserves a clean boundary for future backend code and matches the existing `frontend/` ownership directory.

## Domain and state model

Shared TypeScript domain types are the sole UI-facing model for invoices, documents, document analysis, Risk Passport, blockchain transactions, and A2A agent traces. A shared status module defines all MVP invoice statuses, Korean status labels, allowed mock transitions, and the simplified supplier registration step:

```text
REGISTER -> BUYER_REVIEW -> VERIFIED
```

All demo values come from a single scenario module. Its invoice and settlement values use the authoritative MVP constants: `INV-2026-001`, KRW 20,000,000, 18,800 USDC supplier advance, 19,800 USDC investor settlement, and 200 USDC platform fee. No supplier residual is displayed or calculated.

## API boundary

Visual components call only query and mutation hooks. Hooks call API modules, which use a selected adapter:

```text
component -> query/mutation hook -> domain API module -> selected adapter
                                                 -> mock adapter
                                                 -> real HTTP adapter
```

`VITE_USE_MOCK_API=true` selects the mock adapter; `false` selects the real adapter. The real adapter uses `VITE_API_BASE_URL` plus `/api/v1` and supports these endpoints:

```text
POST /invoices
GET  /invoices
GET  /invoices/{invoiceId}
POST /invoices/{invoiceId}/verification-request
GET  /verifications
GET  /verifications/{id}
POST /verifications/{verificationId}/confirm
POST /invoices/{invoiceId}/offer-response
GET  /investor/dashboard
POST /invoices/{invoiceId}/settlement/mock-payment
```

The real adapter is the only location permitted to make `fetch` calls. Until backend DTOs are merged, mapping functions will document the required response fields and fail clearly for missing required data rather than guessing business rules.

## Mock demo flow

The mock adapter is an in-memory state machine for the one happy-path invoice. The developer route can progress it through:

```text
reset -> document analysis -> buyer confirmation -> Risk Passport
-> supplier offer acceptance -> Treasury funding -> KRW mock payment -> settlement
```

It represents the MVP boundaries accurately: Gemini analysis output is already returned by the backend boundary; risk and policy outcomes are display data; the KRW event is visibly a sandbox event; and transaction receipts are demo records, not wallet actions.

Buyer revision and dispute controls only change the applicable status. They do not add a resolution workflow.

## Routes and screens

- `/supplier`: supplier dashboard with account summary, invoice list, and new-invoice link.
- `/supplier/invoices/new`: four typed document slots, file validation, upload/replacement/removal, and analysis request.
- `/supplier/invoices/:invoiceId`: one detail route that swaps state sections, including offer, funding, and settlement receipts.
- `/buyer`: verification-request and payment-due lists.
- `/buyer/invoices/:invoiceId`: verification form or mock maturity-payment state based on invoice status.
- `/investor/setup`: mandate and policy setup shell that invokes APIs only; it never performs AP2 or gasless logic in-browser.
- `/investor`: investor dashboard.
- `/investor/activities/:invoiceId`: Risk Passport, policy/AP2 results, trace, and transaction/settlement records.
- `/dev/demo`: non-navigation demo controls that use the same hooks as the product routes.

Shared accessible components include layout and development-only role switching, loading/error/empty states, status badge, upload card, PDF preview shell, extracted-field row, supplier progress, Risk Passport summary, trace list, transaction receipt, and Explorer link. Styling is intentionally minimal semantic HTML and basic CSS.

## Validation and error behavior

The upload flow permits one file per required document type, only PDF/JPG/JPEG/PNG files, and a maximum of 20 MB per file. Analysis remains disabled until all four slots have valid completed uploads. Every mutation invalidates the relevant invoice, invoice-list, verification-list, or dashboard query. Loading, API errors, invalid file errors, and unavailable PDF preview states are shown explicitly.

## Test strategy

Tests are written before production behavior. They cover observable behavior rather than implementation details:

- status labels, supplier step mapping, and permitted mock transitions;
- permitted/rejected file types and the 20 MB boundary;
- mock adapter end-to-end transition effects;
- Explorer link construction;
- document-analysis control disabled until four valid documents exist;
- representative buyer-review, offer-ready, funded, and settled screen states.

Before reporting completion, run the configured `lint`, `typecheck`, `test`, and `build` scripts. Any missing backend DTO or API error remains a reported integration issue, not a silently invented contract.

## Explicit integration follow-up

When the backend branch is merged, replace the real adapter's temporary response mapping with the actual DTOs. The backend team must provide or commit:

1. `POST /invoices` multipart field names and its invoice/analysis response;
2. list/detail invoice response schemas;
3. verification identifiers and confirm request/response schemas;
4. offer-response request shape;
5. investor dashboard schema; and
6. mock-payment response and the transaction/settlement record schemas.
