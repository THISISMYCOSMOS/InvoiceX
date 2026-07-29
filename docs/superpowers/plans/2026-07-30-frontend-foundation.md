# InvoiceX Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the role-based InvoiceX MVP frontend foundation with a testable mock scenario and a switchable `/api/v1` HTTP adapter.

**Architecture:** The `frontend/` directory becomes an isolated React application. UI components use React Router and TanStack Query hooks only; hooks call domain API modules; modules select either a memory-backed mock adapter or a real HTTP adapter. Shared domain types and status mapping own all business-facing UI labels and demo constants.

**Tech Stack:** Vite, React, TypeScript, React Router, TanStack Query, Vitest, Testing Library, minimal CSS.

## Global Constraints

- Work on the existing `feat-frontend` branch; never add the user-provided untracked source documents to a commit.
- Target `/api/v1` through an adapter; do not retain the request document's older `/api/...` API examples.
- Use `VITE_USE_MOCK_API=true` by default and `VITE_API_BASE_URL` for real API mode.
- Do not implement frontend Gemini calls, risk scoring, AP2 verification, gasless transactions, wallet signing, or Solana money movement.
- Keep all shared demo values in `src/mocks/demoScenario.ts`; do not hard-code financial values in screens.
- Use the authoritative MVP values: `INV-2026-001`, KRW 20,000,000, advance 18,800 USDC, investor settlement 19,800 USDC, platform fee 200 USDC, supplier residual 0 USDC.
- Allow only PDF/JPG/JPEG/PNG uploads, at most one file per required type, and a maximum of 20 MB per file.
- Use the supplier CTA `조건 동의 및 조기정산 신청`; never show an RWA issuance CTA.
- Keep status labels outside JSX and render state-specific sections within shared detail routes.
- Keep design semantic and minimally styled; do not add a design system, animations, real authentication, or advanced responsive behavior.
- Run `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build` from `frontend/` before completion.

---

## File Structure

```text
frontend/
├── package.json                         # scripts and frontend dependencies
├── vite.config.ts                       # Vite and Vitest configuration
├── tsconfig.json                        # strict TypeScript configuration
├── index.html
├── src/
│   ├── main.tsx                         # QueryClient and BrowserRouter bootstrap
│   ├── App.tsx                          # application routes
│   ├── styles.css                       # minimal accessible layout styles
│   ├── api/
│   │   ├── client.ts                    # adapter selection and HttpError
│   │   ├── invoices.api.ts               # invoice/offer domain API
│   │   ├── verifications.api.ts          # verification domain API
│   │   ├── investor.api.ts               # investor domain API
│   │   ├── settlement.api.ts             # mock-payment domain API
│   │   ├── demo.api.ts                   # developer demo domain API
│   │   └── adapters/
│   │       ├── contracts.ts              # adapter interface and server DTO boundary
│   │       ├── mockAdapter.ts            # in-memory scenario state machine
│   │       └── httpAdapter.ts            # the only fetch caller
│   ├── components/                       # reusable presentational components
│   ├── hooks/                            # TanStack Query wrappers only
│   ├── mocks/demoScenario.ts             # one authoritative screen scenario
│   ├── pages/                            # role route pages and state sections
│   ├── types/                            # domain types and status mapping
│   └── utils/fileValidation.ts           # pure document validation
└── src/**/*.test.ts(x)                   # co-located behavior tests
```

### Task 1: Bootstrap a testable React application

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/App.test.tsx`

**Interfaces:**
- Produces `App`, the root component later supplied with routes and a QueryClient.
- Produces the scripts `dev`, `build`, `lint`, `typecheck`, and `test`.

- [ ] **Step 1: Add a failing application smoke test**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";

test("renders the InvoiceX application heading", () => {
  render(<App />, { wrapper: MemoryRouter });
  expect(screen.getByRole("heading", { name: "InvoiceX" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify that it fails**

Run: `npm test -- App.test.tsx`

Expected: FAIL because the Vite test configuration and `App` implementation do not exist.

- [ ] **Step 3: Create the minimal application configuration and root implementation**

```tsx
export function App() {
  return <main><h1>InvoiceX</h1></main>;
}
```

Configure Vitest with the `jsdom` environment and Testing Library setup. In `main.tsx`, create one `QueryClient`, then render `<QueryClientProvider><BrowserRouter><App /></BrowserRouter></QueryClientProvider>` into `#root`. Add strict TypeScript, a no-output typecheck script, and basic ESLint rules. Do not add application behavior yet.

- [ ] **Step 4: Run the smoke test and static checks**

Run: `npm test -- App.test.tsx && npm run typecheck && npm run build`

Expected: PASS; the production bundle is generated with no TypeScript errors.

- [ ] **Step 5: Commit the bootstrap deliverable**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src/main.tsx frontend/src/App.tsx frontend/src/styles.css frontend/src/App.test.tsx
git commit -m "feat: bootstrap frontend application"
```

### Task 2: Define the shared domain, scenario, and pure validation utilities

**Files:**
- Create: `frontend/src/types/invoice.ts`
- Create: `frontend/src/types/documents.ts`
- Create: `frontend/src/types/agents.ts`
- Create: `frontend/src/mocks/demoScenario.ts`
- Create: `frontend/src/utils/fileValidation.ts`
- Test: `frontend/src/types/invoice.test.ts`
- Test: `frontend/src/utils/fileValidation.test.ts`

**Interfaces:**
- Produces `InvoiceStatus`, `getInvoiceStatusLabel(status)`, and `getSupplierRegistrationStep(status)`.
- Produces `Invoice`, `InvoiceDocument`, `DocumentAnalysis`, `RiskPassport`, `BlockchainTransaction`, `AgentTrace`, and `InvestorDashboard` domain types.
- Produces `DEMO_INVOICE`, `DEMO_SETTLEMENT`, `REQUIRED_DOCUMENT_TYPES`, and `validateDocumentFile(file)`.

- [ ] **Step 1: Write failing status and validation tests**

```ts
import { getInvoiceStatusLabel, getSupplierRegistrationStep } from "./invoice";
import { validateDocumentFile } from "../utils/fileValidation";

test("maps buyer review to the supplier buyer-review step", () => {
  expect(getSupplierRegistrationStep("BUYER_REVIEW")).toBe("BUYER_REVIEW");
  expect(getInvoiceStatusLabel("FUNDED")).toBe("USDC 지급 완료");
});

test("rejects a document larger than 20 MB", () => {
  const file = new File([new Uint8Array(20 * 1024 * 1024 + 1)], "invoice.pdf", { type: "application/pdf" });
  expect(validateDocumentFile(file)).toEqual({ valid: false, message: "파일은 20MB 이하여야 합니다." });
});
```

- [ ] **Step 2: Run the focused tests to verify that they fail**

Run: `npm test -- invoice.test.ts fileValidation.test.ts`

Expected: FAIL because the modules and exported functions do not exist.

- [ ] **Step 3: Implement the minimal shared models and utilities**

```ts
export type SupplierRegistrationStep = "REGISTER" | "BUYER_REVIEW" | "VERIFIED";

export function getSupplierRegistrationStep(status: InvoiceStatus): SupplierRegistrationStep {
  if (["DRAFT", "DOCUMENT_UPLOADING", "DOCUMENT_ANALYZING", "DOCUMENT_REVIEW_REQUIRED"].includes(status)) return "REGISTER";
  return status === "BUYER_REVIEW" ? "BUYER_REVIEW" : "VERIFIED";
}
```

Define all requested state/type fields from the frontend request, including the four document types. Define status labels centrally in `Record<InvoiceStatus, string>`. Put fixed actors, document metadata, Risk Passport facts, trace records, transaction records, and settlement numbers in `demoScenario.ts`. `validateDocumentFile` must accept only the four permitted MIME types or recognized filename extensions and return `{ valid: true }` otherwise.

- [ ] **Step 4: Run the focused tests to verify that they pass**

Run: `npm test -- invoice.test.ts fileValidation.test.ts`

Expected: PASS; the boundary test accepts exactly 20 MB and rejects 20 MB plus one byte.

- [ ] **Step 5: Commit the shared model deliverable**

```bash
git add frontend/src/types frontend/src/mocks/demoScenario.ts frontend/src/utils/fileValidation.ts frontend/src/types/invoice.test.ts frontend/src/utils/fileValidation.test.ts
git commit -m "feat: add shared invoice domain and demo scenario"
```

### Task 3: Build the adapter boundary and the Mock scenario state machine

**Files:**
- Create: `frontend/src/api/adapters/contracts.ts`
- Create: `frontend/src/api/adapters/mockAdapter.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/invoices.api.ts`
- Create: `frontend/src/api/verifications.api.ts`
- Create: `frontend/src/api/investor.api.ts`
- Create: `frontend/src/api/settlement.api.ts`
- Create: `frontend/src/api/demo.api.ts`
- Test: `frontend/src/api/adapters/mockAdapter.test.ts`

**Interfaces:**
- Consumes the domain types and constants from Task 2.
- Produces `InvoiceApi`, `VerificationApi`, `InvestorApi`, `SettlementApi`, `DemoApi`, `resetDemoState()`, and `createMockAdapter()`.
- Each adapter method returns domain types, never raw backend JSON.

- [ ] **Step 1: Write a failing end-to-end Mock transition test**

```ts
import { createMockAdapter } from "./mockAdapter";

test("progresses the demo invoice from analysis to settled", async () => {
  const adapter = createMockAdapter();
  await adapter.analyzeInvoice("INV-2026-001");
  await adapter.requestVerification("INV-2026-001");
  await adapter.confirmVerification("VER-2026-001");
  await adapter.respondToOffer("INV-2026-001", "ACCEPT");
  await adapter.runFunding("INV-2026-001");
  await adapter.mockPayment("INV-2026-001");
  await adapter.runSettlement("INV-2026-001");
  const invoice = await adapter.getInvoice("INV-2026-001");
  expect(invoice.status).toBe("SETTLED");
  expect(invoice.settlement?.investorSettlementUsdc).toBe(19_800);
});
```

- [ ] **Step 2: Run the Mock adapter test to verify that it fails**

Run: `npm test -- mockAdapter.test.ts`

Expected: FAIL because `createMockAdapter` and its transition methods do not exist.

- [ ] **Step 3: Implement the adapter contract and minimal state machine**

```ts
export interface ScenarioAdapter {
  getInvoices(): Promise<Invoice[]>;
  getInvoice(invoiceId: string): Promise<Invoice>;
  analyzeInvoice(invoiceId: string): Promise<Invoice>;
  requestVerification(invoiceId: string): Promise<Invoice>;
  getVerifications(): Promise<VerificationRequest[]>;
  getVerification(verificationId: string): Promise<VerificationRequest>;
  confirmVerification(verificationId: string): Promise<Invoice>;
  respondToOffer(invoiceId: string, response: "ACCEPT" | "DECLINE"): Promise<Invoice>;
  runFunding(invoiceId: string): Promise<Invoice>;
  runSettlement(invoiceId: string): Promise<Invoice>;
  getInvestorDashboard(): Promise<InvestorDashboard>;
  mockPayment(invoiceId: string): Promise<Invoice>;
  reset(): Promise<Invoice>;
}
```

Copy the base scenario per adapter instance. Model the explicit happy-path transitions: analyzing completes to `DOCUMENT_REVIEW_REQUIRED`; verification request changes to `BUYER_REVIEW`; confirm creates the deterministic Risk Passport and moves to `OFFER_READY`; accepted offer moves through funding to `FUNDED`; mock payment moves to `SETTLING`; settlement completes to `SETTLED` with the fixed transaction and settlement values. Return a rejected Promise with an invoice-specific error for an invalid transition. Keep revision/dispute to status-only helper methods.

- [ ] **Step 4: Run the adapter test to verify that it passes**

Run: `npm test -- mockAdapter.test.ts`

Expected: PASS; all transition calls return the same invoice ID and the final invoice includes the 19,800 USDC settlement record.

- [ ] **Step 5: Commit the Mock API deliverable**

```bash
git add frontend/src/api frontend/src/api/adapters/mockAdapter.test.ts
git commit -m "feat: add mock api adapter and demo scenario"
```

### Task 4: Add the real `/api/v1` HTTP adapter and adapter-selection tests

**Files:**
- Create: `frontend/src/api/adapters/httpAdapter.ts`
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/api/adapters/httpAdapter.test.ts`

**Interfaces:**
- Consumes `ScenarioAdapter` from Task 3.
- Produces `createHttpAdapter(fetchImpl, baseUrl)` and `getScenarioAdapter()`.
- `fetchImpl` enables real contract tests without a network request.

- [ ] **Step 1: Write failing HTTP contract tests**

```ts
import { createHttpAdapter } from "./httpAdapter";

test("uses the supplied v1 invoice list endpoint", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [] }), { status: 200 }));
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");
  await adapter.getInvoices();
  expect(fetchImpl).toHaveBeenCalledWith("https://api.example.com/api/v1/invoices", expect.objectContaining({ method: "GET" }));
});
```

- [ ] **Step 2: Run the contract test to verify that it fails**

Run: `npm test -- httpAdapter.test.ts`

Expected: FAIL because the HTTP adapter does not exist.

- [ ] **Step 3: Implement the minimal HTTP adapter and explicit DTO mapping**

```ts
export function createHttpAdapter(fetchImpl: typeof fetch, baseUrl: string): ScenarioAdapter {
  const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
    const response = await fetchImpl(`${baseUrl}${path}`, init);
    if (!response.ok) throw new HttpError(response.status, await response.text());
    return response.json() as Promise<T>;
  };
  // Map each endpoint response into domain types here.
}
```

Use `POST /invoices` with `FormData` for document creation, `GET /invoices`, `GET /invoices/{invoiceId}`, the four verification endpoints, `POST /invoices/{invoiceId}/offer-response`, `GET /investor/dashboard`, and `POST /invoices/{invoiceId}/settlement/mock-payment`. Mapping functions must validate required IDs/statuses and throw `HttpError` with a clear message when the backend response lacks them. Select the mock adapter unless `import.meta.env.VITE_USE_MOCK_API === "false"`.

- [ ] **Step 4: Run adapter tests to verify that they pass**

Run: `npm test -- mockAdapter.test.ts httpAdapter.test.ts`

Expected: PASS; the adapter sends the exact `/api/v1` list path and reports non-2xx responses as `HttpError`.

- [ ] **Step 5: Commit the real API boundary**

```bash
git add frontend/src/api/adapters/httpAdapter.ts frontend/src/api/client.ts frontend/src/api/adapters/httpAdapter.test.ts
git commit -m "feat: add switchable v1 api adapter"
```

### Task 5: Expose API operations through Query and Mutation hooks

**Files:**
- Create: `frontend/src/hooks/queryKeys.ts`
- Create: `frontend/src/hooks/useInvoice.ts`
- Create: `frontend/src/hooks/useInvoices.ts`
- Create: `frontend/src/hooks/useDocumentAnalysis.ts`
- Create: `frontend/src/hooks/useBuyerConfirm.ts`
- Create: `frontend/src/hooks/useAcceptOffer.ts`
- Create: `frontend/src/hooks/useSettlement.ts`
- Create: `frontend/src/hooks/useInvestorDashboard.ts`
- Create: `frontend/src/hooks/useDemoControl.ts`
- Test: `frontend/src/hooks/useBuyerConfirm.test.tsx`

**Interfaces:**
- Consumes the domain API modules from Tasks 3 and 4.
- Produces query hooks returning TanStack Query result objects and mutation hooks that invalidate `invoice`, `invoices`, `verifications`, and `investorDashboard` keys.

- [ ] **Step 1: Write a failing invalidation behavior test**

```tsx
test("invalidates invoice and verification queries after buyer confirmation", async () => {
  const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
  const { result } = renderHook(() => useBuyerConfirm(), { wrapper });
  await act(() => result.current.mutateAsync("VER-2026-001"));
  expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["invoice", "INV-2026-001"] });
  expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["verifications"] });
});
```

- [ ] **Step 2: Run the hook test to verify that it fails**

Run: `npm test -- useBuyerConfirm.test.tsx`

Expected: FAIL because the hook does not exist.

- [ ] **Step 3: Implement focused hooks with shared keys**

```ts
export const queryKeys = {
  invoice: (invoiceId: string) => ["invoice", invoiceId] as const,
  invoices: ["invoices"] as const,
  verifications: ["verifications"] as const,
  investorDashboard: ["investorDashboard"] as const,
};
```

Use `useQuery` only for reads and `useMutation` only for state changes. On every successful mutation, invalidate the exact related keys. Do not call `fetch` or include UI rendering inside hooks.

- [ ] **Step 4: Run the hook test to verify that it passes**

Run: `npm test -- useBuyerConfirm.test.tsx`

Expected: PASS; confirmation invalidates the invoice and verification list.

- [ ] **Step 5: Commit the hook layer**

```bash
git add frontend/src/hooks frontend/src/hooks/useBuyerConfirm.test.tsx
git commit -m "feat: add invoice query hooks"
```

### Task 6: Implement shared presentational components and document upload behavior

**Files:**
- Create: `frontend/src/components/AppLayout.tsx`
- Create: `frontend/src/components/RoleSwitcher.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/components/LoadingState.tsx`
- Create: `frontend/src/components/ErrorState.tsx`
- Create: `frontend/src/components/EmptyState.tsx`
- Create: `frontend/src/components/DocumentUploadCard.tsx`
- Create: `frontend/src/components/PdfViewer.tsx`
- Create: `frontend/src/components/ExtractedFieldRow.tsx`
- Create: `frontend/src/components/InvoiceProgress.tsx`
- Create: `frontend/src/components/RiskPassportSummary.tsx`
- Create: `frontend/src/components/AgentTraceList.tsx`
- Create: `frontend/src/components/ExplorerLink.tsx`
- Create: `frontend/src/components/TransactionReceipt.tsx`
- Test: `frontend/src/components/DocumentUploadCard.test.tsx`
- Test: `frontend/src/components/ExplorerLink.test.tsx`

**Interfaces:**
- Consumes domain types from Task 2 and validation from Task 2.
- Produces presentational components that receive data and callbacks through props; none call hooks or API modules.

- [ ] **Step 1: Write failing upload-control and Explorer-link tests**

```tsx
test("disables analysis until all four valid documents are complete", () => {
  render(<DocumentUploadCard documents={threeCompletedDocuments} onChange={vi.fn()} onAnalyze={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Document Agent 분석 실행" })).toBeDisabled();
});

test("links a transaction to Solana Explorer devnet", () => {
  render(<ExplorerLink signature="5ig" />);
  expect(screen.getByRole("link", { name: "Solana Explorer에서 보기" })).toHaveAttribute("href", "https://explorer.solana.com/tx/5ig?cluster=devnet");
});
```

- [ ] **Step 2: Run the component tests to verify that they fail**

Run: `npm test -- DocumentUploadCard.test.tsx ExplorerLink.test.tsx`

Expected: FAIL because the components do not exist.

- [ ] **Step 3: Implement minimal accessible shared components**

```tsx
export function ExplorerLink({ signature }: { signature: string }) {
  return <a href={`https://explorer.solana.com/tx/${encodeURIComponent(signature)}?cluster=devnet`} target="_blank" rel="noreferrer">Solana Explorer에서 보기</a>;
}
```

`DocumentUploadCard` must render a labeled native file input per document type, accept drag/drop, run `validateDocumentFile`, expose replace/remove actions, and compute analysis enabled only when all `REQUIRED_DOCUMENT_TYPES` are `COMPLETED`. `PdfViewer` uses an object URL for local PDFs and displays an explicit unsupported/unavailable message for images or absent files. `RoleSwitcher` renders only when `import.meta.env.DEV` is true. `TransactionReceipt` displays hash, status, amount, source, destination, network, and Explorer link.

- [ ] **Step 4: Run the component tests to verify that they pass**

Run: `npm test -- DocumentUploadCard.test.tsx ExplorerLink.test.tsx`

Expected: PASS; three documents keep analysis disabled, four valid completed documents enable it, and Explorer uses devnet.

- [ ] **Step 5: Commit shared components**

```bash
git add frontend/src/components frontend/src/components/DocumentUploadCard.test.tsx frontend/src/components/ExplorerLink.test.tsx
git commit -m "feat: add shared invoice components"
```

### Task 7: Implement supplier routes and status-specific invoice detail sections

**Files:**
- Create: `frontend/src/pages/supplier/SupplierDashboardPage.tsx`
- Create: `frontend/src/pages/supplier/NewInvoicePage.tsx`
- Create: `frontend/src/pages/supplier/SupplierInvoiceDetailPage.tsx`
- Create: `frontend/src/pages/supplier/sections/BuyerReviewPendingSection.tsx`
- Create: `frontend/src/pages/supplier/sections/EarlySettlementOfferSection.tsx`
- Create: `frontend/src/pages/supplier/sections/FundingProgressSection.tsx`
- Create: `frontend/src/pages/supplier/sections/FundingReceiptSection.tsx`
- Create: `frontend/src/pages/supplier/sections/SettlementReceiptSection.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/pages/supplier/SupplierInvoiceDetailPage.test.tsx`

**Interfaces:**
- Consumes supplier hooks from Task 5 and components from Task 6.
- Produces `/supplier`, `/supplier/invoices/new`, and `/supplier/invoices/:invoiceId` routes.

- [ ] **Step 1: Write failing status-section behavior tests**

```tsx
test("shows the early settlement CTA for an offer-ready invoice", () => {
  renderSupplierDetail({ status: "OFFER_READY" });
  expect(screen.getByRole("button", { name: "조건 동의 및 조기정산 신청" })).toBeInTheDocument();
});

test("shows the transaction receipt for a funded invoice", () => {
  renderSupplierDetail({ status: "FUNDED", fundingTransaction: demoTransaction });
  expect(screen.getByText("Transaction Hash")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the page tests to verify that they fail**

Run: `npm test -- SupplierInvoiceDetailPage.test.tsx`

Expected: FAIL because the supplier pages and state sections do not exist.

- [ ] **Step 3: Implement supplier screens with one status-switching detail route**

```tsx
switch (invoice.status) {
  case "BUYER_REVIEW": return <BuyerReviewPendingSection invoice={invoice} />;
  case "OFFER_READY": return <EarlySettlementOfferSection invoice={invoice} onAccept={acceptOffer} />;
  case "FUNDING": return <FundingProgressSection />;
  case "FUNDED": return <FundingReceiptSection transaction={invoice.fundingTransaction!} />;
  case "SETTLED": return <SettlementReceiptSection settlement={invoice.settlement!} />;
  default: return <InvoiceDefaultSection invoice={invoice} />;
}
```

The dashboard displays Alpha Components, current/received USDC, in-progress count, invoice list, and new-invoice link. The new-invoice page owns local selected-file state and calls the document analysis hook only after four successful slots. The detail page renders `InvoiceProgress` using the shared supplier-step mapping and must not add separate detail routes per status.

- [ ] **Step 4: Run the supplier page tests to verify that they pass**

Run: `npm test -- SupplierInvoiceDetailPage.test.tsx`

Expected: PASS; the offer CTA and funded receipt appear only in their matching states.

- [ ] **Step 5: Commit the supplier flow**

```bash
git add frontend/src/pages/supplier frontend/src/App.tsx frontend/src/pages/supplier/SupplierInvoiceDetailPage.test.tsx
git commit -m "feat: add supplier invoice flow"
```

### Task 8: Implement buyer and investor routes

**Files:**
- Create: `frontend/src/pages/buyer/BuyerDashboardPage.tsx`
- Create: `frontend/src/pages/buyer/BuyerInvoiceDetailPage.tsx`
- Create: `frontend/src/pages/investor/InvestorSetupPage.tsx`
- Create: `frontend/src/pages/investor/InvestorDashboardPage.tsx`
- Create: `frontend/src/pages/investor/InvestorActivityPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/pages/buyer/BuyerInvoiceDetailPage.test.tsx`
- Test: `frontend/src/pages/investor/InvestorActivityPage.test.tsx`

**Interfaces:**
- Consumes verification, investor, offer, and settlement hooks from Task 5.
- Produces buyer and investor route components; all actions flow through hooks.

- [ ] **Step 1: Write failing buyer and investor screen tests**

```tsx
test("shows verification controls for a buyer-review invoice", () => {
  renderBuyerDetail({ status: "BUYER_REVIEW" });
  expect(screen.getByRole("button", { name: "확인 완료" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "이의 제기" })).toBeInTheDocument();
});

test("shows Agent Trace and transaction data for the investor activity", () => {
  renderInvestorActivity(demoInvestorActivity);
  expect(screen.getByText("Risk Agent → Treasury Agent")).toBeInTheDocument();
  expect(screen.getByText("Solana Transaction Hash")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the route tests to verify that they fail**

Run: `npm test -- BuyerInvoiceDetailPage.test.tsx InvestorActivityPage.test.tsx`

Expected: FAIL because these pages do not exist.

- [ ] **Step 3: Implement minimal buyer and investor screens**

```tsx
<button onClick={() => confirmMutation.mutate(verificationId)} disabled={confirmMutation.isPending}>
  확인 완료
</button>
```

The buyer dashboard separates verification requests and payments due. The buyer detail displays document/analysis facts, transaction/delivery/dispute checks, Confirm, revision, and dispute status-only controls; its maturity state labels KRW payment as a Mock settlement-partner event. Investor setup displays wallet/vault/policy/mandate fields but invokes only API interfaces; no browser-side AP2 or gasless logic. Investor dashboard shows activation, mandate status, available vault amount, outstanding principal, and recent Treasury activity. Activity displays the Risk Passport, policy/AP2 result records, trace, funding transaction, and settlement receipt.

- [ ] **Step 4: Run the route tests to verify that they pass**

Run: `npm test -- BuyerInvoiceDetailPage.test.tsx InvestorActivityPage.test.tsx`

Expected: PASS; buyer controls render for buyer review and the investor view shows trace plus transaction details.

- [ ] **Step 5: Commit buyer and investor route shells**

```bash
git add frontend/src/pages/buyer frontend/src/pages/investor frontend/src/App.tsx frontend/src/pages/buyer/BuyerInvoiceDetailPage.test.tsx frontend/src/pages/investor/InvestorActivityPage.test.tsx
git commit -m "feat: add buyer and investor frontend shells"
```

### Task 9: Implement the development-only demo control route

**Files:**
- Create: `frontend/src/pages/dev/DemoControlPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/pages/dev/DemoControlPage.test.tsx`

**Interfaces:**
- Consumes `useDemoControl` and `useInvoice` from Task 5.
- Produces the `/dev/demo` route with eight state-control actions.

- [ ] **Step 1: Write a failing ordered-control test**

```tsx
test("enables buyer confirmation after document analysis succeeds", async () => {
  render(<DemoControlPage />);
  expect(screen.getByRole("button", { name: "Buyer Confirm" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Document Agent 분석 실행" }));
  expect(await screen.findByRole("button", { name: "Buyer Confirm" })).toBeEnabled();
});
```

- [ ] **Step 2: Run the demo page test to verify that it fails**

Run: `npm test -- DemoControlPage.test.tsx`

Expected: FAIL because the route and controls do not exist.

- [ ] **Step 3: Implement state-aware demo controls**

```tsx
const controls = [
  ["전체 데모 데이터 초기화", reset],
  ["Document Agent 분석 실행", analyze],
  ["Buyer Confirm", confirm],
  ["Risk Passport 생성", createPassport],
  ["공급기업 조건 동의", acceptOffer],
  ["Treasury Agent 투자 실행", fund],
  ["원화 입금 Mock 이벤트 발생", mockPayment],
  ["Settlement 실행", settle],
] as const;
```

Render the exact eight controls requested. Enable each only when its corresponding server/Mock action is currently valid; show mutation pending/error state. In Mock mode they advance the state machine. In real mode they invoke the applicable endpoint, while unsupported separate risk/funding/settlement calls show a clear backend-integration notice instead of simulating a real payment.

- [ ] **Step 4: Run the demo route test to verify that it passes**

Run: `npm test -- DemoControlPage.test.tsx`

Expected: PASS; confirmation becomes available only after the preceding analysis action.

- [ ] **Step 5: Commit demo controls**

```bash
git add frontend/src/pages/dev frontend/src/App.tsx frontend/src/pages/dev/DemoControlPage.test.tsx
git commit -m "feat: add demo control panel"
```

### Task 10: Finish integration tests and operating documentation

**Files:**
- Create: `frontend/README.md`
- Modify: `frontend/src/App.test.tsx`
- Create: `frontend/src/pages/routes.test.tsx`
- Modify: `frontend/package.json`

**Interfaces:**
- Consumes all completed routes and scripts.
- Produces documented setup, Mock/real API switching instructions, endpoint assumptions, and verification commands.

- [ ] **Step 1: Write a failing role-route integration test**

```tsx
test.each([
  ["/supplier", "Alpha Components"],
  ["/buyer", "확인이 필요한 인보이스"],
  ["/investor", "Nova Capital"],
  ["/dev/demo", "전체 데모 데이터 초기화"],
])("renders %s", (path, expectedText) => {
  renderAt(path);
  expect(screen.getByText(expectedText)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the integration test to verify that it fails**

Run: `npm test -- routes.test.tsx`

Expected: FAIL until every role route is registered with its final page.

- [ ] **Step 3: Complete route registration and write operating documentation**

Register every required route in `App.tsx`; keep `/dev/demo` out of normal app navigation. Document Node/npm prerequisites, `npm install`, `npm run dev`, all four verification commands, environment variables, Mock mode default, real `/api/v1` mode, and the six missing backend DTO contracts. Do not document unimplemented wallet/Gemini/AP2 behavior as available.

- [ ] **Step 4: Run focused and complete verification**

Run: `npm test -- routes.test.tsx && npm run lint && npm run typecheck && npm run test && npm run build`

Expected: PASS with no lint, typecheck, test, or build failure.

- [ ] **Step 5: Commit the verified frontend foundation**

```bash
git add frontend/README.md frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/pages/routes.test.tsx frontend/package.json
git commit -m "test: verify frontend foundation"
```

## Self-Review

- [x] Spec coverage: Tasks 1–10 cover the isolated frontend, all required role routes, shared types/statuses, demo data, Mock/real adapter switch, hooks, document upload and preview, state-specific detail views, transaction display, developer controls, tests, and operating documentation.
- [x] MVP scope: no task adds login, wallet keys, Gemini calls, AP2 validation, Solana transfers, financial calculations, or a final design system.
- [x] API contract: only the supplied `/api/v1` routes appear in the HTTP adapter; unresolved DTOs stay isolated and documented.
- [x] Type consistency: `ScenarioAdapter`, `InvoiceStatus`, domain Invoice types, `queryKeys`, and component inputs are defined before their consumers.
- [x] Placeholder scan: no `TODO`, `TBD`, “implement later”, or unspecified testing steps remain.
