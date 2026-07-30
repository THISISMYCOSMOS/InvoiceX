# InvoiceX Supplier Figma Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the five supplied Figma screens as a faithful, functional supplier flow without changing the existing API-adapter architecture.

**Architecture:** Keep page components dependent on TanStack Query hooks and domain API modules only. Add a route-aware application shell, a demo-only login route, and state-specific supplier detail sections. Preserve the mock/HTTP adapter swap and the user's polling changes.

**Tech Stack:** React 19, TypeScript, Vite, React Router 7, TanStack Query 5, Tailwind CSS 4, Vitest, Testing Library.

## Global Constraints

- Match the five supplied Figma nodes at the 1440 × 900 reference viewport.
- Preserve all existing API contracts and the `ScenarioAdapter` boundary.
- Preserve uncommitted `useInvoice` and `invoicePolling` changes.
- Do not implement real authentication.
- Do not call `fetch` from components.
- Use a maintained icon package; do not create custom SVG or CSS icons.
- Preserve accessible loading, validation, mutation-error, and missing-analysis states.
- Follow red-green-refactor for every new behavior.

---

## File structure

```text
frontend/src/
├── App.tsx
├── styles.css
├── components/
│   ├── AppLayout.tsx
│   ├── Brand.tsx
│   └── DocumentUploadCard.tsx
├── hooks/
│   └── useRequestVerification.ts
└── pages/
    ├── LoginPage.tsx
    └── supplier/
        ├── SupplierDashboardPage.tsx
        ├── NewInvoicePage.tsx
        ├── SupplierInvoiceDetailPage.tsx
        └── sections/
            ├── DocumentReviewSection.tsx
            └── BuyerReviewPendingSection.tsx
```

### Task 1: Login route and shared shell

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/components/Brand.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/pages/routes.test.tsx`

**Interfaces:**
- `LoginPage()` navigates the selected role on form submit.
- `AppLayout({ children })` renders route-aware navigation around authenticated demo routes.
- `Brand()` renders the shared InvoiceX wordmark.

- [ ] **Step 1: Add failing route tests**

Add tests that render `/login`, select each role tab, submit the form, and assert the matching dashboard content appears. A separate assertion verifies the supplier shell exposes “Overview”, “Invoices”, and “Company & Wallet”.

- [ ] **Step 2: Verify the tests fail**

Run: `npm test -- src/pages/routes.test.tsx`

Expected: FAIL because `/login` redirects to the supplier dashboard and the Figma shell is absent.

- [ ] **Step 3: Implement the minimal route and shell**

Move `/login` outside `AppLayout`, redirect unknown routes to `/login`, create the role-tab form, and render the shared top bar/sidebar for supplier paths. Add the Figma desktop measurements and responsive fallback styles.

- [ ] **Step 4: Verify the tests pass**

Run: `npm test -- src/pages/routes.test.tsx`

Expected: PASS with no accessibility or React warnings.

### Task 2: Supplier dashboard

**Files:**
- Modify: `frontend/src/pages/supplier/SupplierDashboardPage.tsx`
- Create or modify: `frontend/src/pages/supplier/SupplierDashboardPage.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `useInvoices(): UseQueryResult<Invoice[]>`.
- Produces: Figma summary cards, recent-invoice table, and new-invoice navigation.

- [ ] **Step 1: Add a failing dashboard behavior test**

Render `/supplier`; assert “Good morning, Minjun”, the four summary cards, a recent-invoices table, and the “New invoice” link to `/supplier/invoices/new`.

- [ ] **Step 2: Verify the test fails**

Run: `npm test -- src/pages/supplier/SupplierDashboardPage.test.tsx`

Expected: FAIL because the current dashboard uses the old Korean summary layout.

- [ ] **Step 3: Implement the dashboard**

Render the exact Figma headings, summary labels, table columns, statuses, and spacing. Keep invoice rows driven by `useInvoices`; format KRW amounts and dates for the visible table.

- [ ] **Step 4: Verify the test passes**

Run: `npm test -- src/pages/supplier/SupplierDashboardPage.test.tsx`

Expected: PASS.

### Task 3: Invoice upload screen

**Files:**
- Modify: `frontend/src/components/DocumentUploadCard.tsx`
- Modify: `frontend/src/components/DocumentUploadCard.test.tsx`
- Modify: `frontend/src/pages/supplier/NewInvoicePage.tsx`
- Create or modify: `frontend/src/pages/supplier/NewInvoicePage.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- `DocumentUploadCard` preserves its current props.
- A successful `useDocumentUpload` result supplies `invoice.id` for navigation.

- [ ] **Step 1: Add failing upload tests**

Assert the four English Figma document labels, allowed-file helper text, disabled analysis before four valid files, enabled analysis after four valid files, and successful navigation to `/supplier/invoices/:invoiceId`.

- [ ] **Step 2: Verify the tests fail**

Run: `npm test -- src/components/DocumentUploadCard.test.tsx src/pages/supplier/NewInvoicePage.test.tsx`

Expected: FAIL because the current component uses the old copy/layout and does not navigate after success.

- [ ] **Step 3: Implement the upload screen**

Restyle the four slots as the Figma two-column grid, retain validation and drag/drop, show selected file metadata and completion state, and navigate after the mutation succeeds.

- [ ] **Step 4: Verify the tests pass**

Run: `npm test -- src/components/DocumentUploadCard.test.tsx src/pages/supplier/NewInvoicePage.test.tsx`

Expected: PASS.

### Task 4: Document Agent review

**Files:**
- Create: `frontend/src/hooks/useRequestVerification.ts`
- Create: `frontend/src/pages/supplier/sections/DocumentReviewSection.tsx`
- Modify: `frontend/src/pages/supplier/SupplierInvoiceDetailPage.tsx`
- Modify: `frontend/src/pages/supplier/SupplierInvoiceDetailPage.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- `useRequestVerification()` calls `invoiceApi.requestVerification(invoiceId)` and invalidates the invoice and invoice-list query keys.
- `DocumentReviewSection({ invoice, onConfirm, isPending })` renders analysis and invokes confirmation.

- [ ] **Step 1: Add a failing review-state test**

Render a `DOCUMENT_REVIEW_REQUIRED` invoice with complete analysis; assert the five visible Figma field groups, the contract-reference warning, document preview, progress step, and “Confirm and continue” behavior.

- [ ] **Step 2: Verify the test fails**

Run: `npm test -- src/pages/supplier/SupplierInvoiceDetailPage.test.tsx`

Expected: FAIL because the current review state renders only an empty heading.

- [ ] **Step 3: Implement the review section and mutation hook**

Render the preview and extracted values from `invoice.analysis`, create the verification mutation, and replace the placeholder review state with the Figma section.

- [ ] **Step 4: Verify the test passes**

Run: `npm test -- src/pages/supplier/SupplierInvoiceDetailPage.test.tsx`

Expected: PASS.

### Task 5: Buyer-verification pending state

**Files:**
- Modify: `frontend/src/pages/supplier/sections/BuyerReviewPendingSection.tsx`
- Modify: `frontend/src/pages/supplier/SupplierInvoiceDetailPage.tsx`
- Modify: `frontend/src/pages/supplier/SupplierInvoiceDetailPage.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- `BuyerReviewPendingSection({ invoice })` receives the current `Invoice`.

- [ ] **Step 1: Add a failing pending-state test**

Assert “Waiting for buyer verification”, buyer name, formatted amount, formatted due date, request timestamp copy, and the highlighted buyer-verification progress step.

- [ ] **Step 2: Verify the test fails**

Run: `npm test -- src/pages/supplier/SupplierInvoiceDetailPage.test.tsx`

Expected: FAIL because the current section does not receive or render invoice details.

- [ ] **Step 3: Implement the pending panel**

Pass the invoice into the section and render the centered Figma card, summary cells, progress track, and notification panel.

- [ ] **Step 4: Verify the test passes**

Run: `npm test -- src/pages/supplier/SupplierInvoiceDetailPage.test.tsx`

Expected: PASS.

### Task 6: Full verification and visual QA

**Files:**
- Create: `frontend/design-qa.md`
- Modify: visual source files above only when QA finds mismatches.

**Interfaces:**
- Produces: a passing `design-qa.md` and locally running verified application.

- [ ] **Step 1: Run the complete automated checks**

Run:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

Expected: all commands exit successfully with no warnings requiring action.

- [ ] **Step 2: Start the application and capture all five states**

Open the application at 1440 × 900 and capture `/login`, `/supplier`, `/supplier/invoices/new`, a `DOCUMENT_REVIEW_REQUIRED` invoice, and a `BUYER_REVIEW` invoice.

- [ ] **Step 3: Compare each capture with its Figma node**

Record mismatches in `frontend/design-qa.md` by priority. Fix P0/P1/P2 issues and repeat the captures until `final result: passed`.

- [ ] **Step 4: Re-run automated checks**

Run the four complete verification commands again after the final visual fixes.
