# InvoiceX Supplier Figma Flow Design

## Purpose and scope

Implement the five supplied Figma frames as one working supplier journey:

1. role-based demo login;
2. supplier dashboard;
3. invoice document registration;
4. Document Agent extraction review; and
5. buyer-verification pending state.

The implementation must preserve the existing React, TanStack Query, domain API, and `ScenarioAdapter` boundaries. It must also preserve the user's uncommitted invoice-polling work. Real authentication remains outside the MVP; login routes the selected demo role to its existing dashboard.

## Visual target

The desktop reference viewport is 1440 × 900. Application screens use a centered 1280 × 800 white shell on `#e8ebf0`, with a 64 px top bar and 200 px sidebar. The primary typeface is Inter with Arial/system fallbacks.

Core tokens:

- primary blue: `#2563eb`;
- dark blue: `#1d4ed8`;
- page background: `#e8ebf0`;
- border: `#d9dee8` and `#cfd5df`;
- main text: `#172033`;
- secondary text: `#64748b` and `#6b7280`;
- success: `#22c55e`;
- warning: `#f59e0b`;
- panel background: `#f8fafc`;
- shell radius: 12 px;
- common component radii: 8–10 px;
- shell shadow: `0 8px 24px rgba(15, 23, 42, 0.06)`.

The login screen uses the same 1280 × 800 shell split into two equal columns. Its left panel uses the exact green-to-violet-to-magenta gradient shown in Figma. The right panel contains the role tabs and functional sign-in form.

## Architecture

### Routing and shell

`/login` renders outside `AppLayout`. All existing role routes remain inside `AppLayout`. Unknown routes redirect to `/login`.

`AppLayout` becomes route-aware. Supplier routes render the Figma top bar, supplier role chip, and supplier navigation while buyer, investor, and developer routes retain working navigation until their matching Figma frames are implemented.

### Data flow

Existing boundaries remain authoritative:

```text
Page -> TanStack Query hook -> domain API module -> ScenarioAdapter
                                                -> mockAdapter or httpAdapter
```

No component calls `fetch` directly. The dashboard reads `useInvoices`. Document registration uses `useDocumentUpload`. Detail screens read `useInvoice`, including the user's polling interval. A new `useRequestVerification` mutation calls the already-defined `invoiceApi.requestVerification`.

### Screen mapping

- Login: new `LoginPage`; selected role determines navigation target.
- Supplier dashboard: restyle `SupplierDashboardPage`; use live invoice data and Figma demo summary values where the current API has no supplier-summary endpoint.
- Invoice registration: retain `DocumentUploadCard` validation and multipart assembly; match Figma's four-card upload grid.
- Extraction review: render when invoice status is `DOCUMENT_REVIEW_REQUIRED`; show the invoice document preview, extracted fields, review warning, and confirmation CTA.
- Approval pending: render when invoice status is `BUYER_REVIEW`; pass the invoice into the status panel and show the exact buyer, amount, due date, and progress state.

## Components

- `LoginPage`: role tabs, email/password inputs, remember checkbox, and sign-in navigation.
- `AppLayout`: responsive outer canvas, product top bar, supplier sidebar, and route content.
- `Brand`: shared InvoiceX wordmark rendered as text.
- `DocumentUploadCard`: functional upload cards with file metadata, validation, drag/drop, replacement, and analysis action.
- `DocumentReviewSection`: extraction progress, PDF-style preview, verified/review-required fields, and verification mutation.
- `BuyerReviewPendingSection`: buyer verification summary and three-step progress.
- Existing `LoadingState`, `ErrorState`, and `StatusBadge` remain the server-state fallbacks.

UI icons come from a maintained icon package; no handcrafted SVG, CSS illustration, emoji, or text-symbol substitute is used.

## Interaction behavior

- Login role tabs are keyboard-operable and expose the selected state.
- Submitting login navigates Supplier to `/supplier`, Buyer to `/buyer`, and Investor to `/investor`.
- “New invoice” navigates to `/supplier/invoices/new`.
- Each document slot accepts PDF, JPG, JPEG, or PNG up to 20 MB using existing validation.
- Analysis remains disabled until all four valid documents exist.
- A successful document submission navigates to the returned invoice detail route.
- “Confirm and continue” requests buyer verification through the adapter and updates the cached invoice.
- Polling remains active only for processing states and stops for stable states according to the user's existing implementation.

## Error and loading behavior

Existing query and mutation errors stay visible through accessible error content. Upload validation is shown within its document slot. Buttons expose pending/disabled states and cannot submit twice. If analysis data is absent while the status requires review, the page shows a recoverable error instead of fabricating values.

## Responsive behavior

At 1440 × 900, measurements match Figma. On narrower displays, the shell uses the available viewport width, the sidebar collapses into a compact horizontal navigation area, dashboard cards wrap, and two-column review/upload content becomes a single column. No desktop element may be cropped at the reference viewport.

## Testing and verification

Behavior tests cover:

- `/login` rendering and role-based navigation;
- supplier dashboard rendering and new-invoice navigation;
- document validation, upload completion, and analysis enablement;
- successful upload navigation to the returned invoice;
- review rendering and verification request transition;
- pending-state invoice data and progress rendering.

Run lint, typecheck, unit/integration tests, and production build. Then compare reference and implementation screenshots at 1440 × 900 for every supplied route/state. Fix all material spacing, typography, color, border, radius, overflow, and interaction differences before handoff.
