# Supplier Figma Flow — Design QA

## Source of truth

- Figma file: `Gmn4FDxT8sXnW45RWWkgL1`
- Login: node `16:316`
- Supplier dashboard: node `16:364`
- Invoice document upload: node `16:478`
- Document Agent review: node `16:568`
- Buyer verification pending: node `16:690`
- Verification viewport: `1440 × 900`

## Captured implementation states

- `.design-qa/implementation-login.png`
- `.design-qa/implementation-supplier-dashboard.png`
- `.design-qa/implementation-supplier-invoice-upload.png`
- `.design-qa/implementation-supplier-invoice-review.png`
- `.design-qa/implementation-supplier-approval-pending.png`

## Interaction verification

The following primary journey was exercised in the in-app browser against the mock ScenarioAdapter:

1. Sign in as Supplier.
2. Open `New invoice`.
3. Upload Invoice, Contract, Purchase order, and Proof of delivery.
4. Run `Analyze documents`.
5. Confirm the Document Agent extraction.
6. Reach the Buyer verification pending state.

The document upload validation, enabled/disabled CTA behavior, route transitions, verification mutation, and pending progress state all behaved as expected.

## Visual comparison history

Each implementation screenshot was compared in the same visual input as its matching Figma node.

- Pass 1: corrected the one-pixel shell overflow, workflow captions, Document Agent badge, buyer legal name, review filename, and upload CTA styling.
- Pass 2: replaced the generic PDF placeholder with a project-local raster invoice preview and matched the Document Agent badge color.
- Pass 3: re-compared the final Document Agent review state against node `16:568`.

## Fidelity review

- Layout: passed — shell, sidebar, header, content widths, card placement, and workflow spacing match the source hierarchy.
- Typography: passed — Inter weights, scale, line-height, and muted text hierarchy match the source.
- Color and borders: passed — blue, slate, green, amber, borders, backgrounds, pills, and radii match the source.
- Assets and icons: passed — Phosphor icons are used for controls and the invoice preview is a real raster asset.
- Responsive safety: passed — desktop source viewport is exact and mobile breakpoints remain usable.
- Browser console: passed — no errors or warnings during the final journey.
- Automated checks: passed — lint, typecheck, 20 test files / 42 tests, and production build.

## Language control addendum

- English remains the default language and the original Figma layout remains unchanged apart from the requested language control.
- Login: the control is the first child of the right panel, remains visible at desktop and mobile widths, and introduces no horizontal overflow.
- Application screens: the control is the first item in the shared top-right user group for Supplier, Buyer, and Investor routes.
- Persistence: switching to Korean updates the document language and survives route changes and a full reload.
- Localization: login, navigation, Supplier flow, Buyer flow, Investor flow, shared status/progress components, and developer demo controls render in both languages.
- Fresh browser session: passed with no console errors or warnings.
- Automated checks: passed — lint, typecheck, 20 test files / 42 tests, and production build.

## Local demo authentication

- Supplier: `supplier@company.com` with the Supplier role.
- Buyer: `buyer@company.com` with the Buyer role.
- Investor: `investor@company.com` with the Investor role.
- Login rejects valid credentials when the selected role does not match.
- Demo sessions persist in browser storage without storing the password.

## Buyer and early-settlement flow

Reference nodes:

- Buyer dashboard: `16:750`
- Buyer verification: `16:833`
- Supplier early-settlement offer: `16:944`
- Buyer due-date payment: `16:1279`

Implementation captures:

- `.design-qa/implementation-buyer-dashboard.png`
- `.design-qa/implementation-buyer-verification.png`
- `.design-qa/implementation-supplier-early-settlement.png`
- `.design-qa/implementation-buyer-payment.png`

Each reference and implementation capture was reviewed together at the 1440 × 900 source state.

- Buyer dashboard: passed — green Buyer navigation, summary cards, request table, and review actions match the source.
- Buyer verification: passed — document tabs, preview, checklist controls, disclosure, status chips, and CTAs match the source.
- Supplier offer: passed with requested product correction — `Early Settlement` and `Transactions` were removed from the sidebar and replaced by `Company & Wallet`; the offer remains a state of the existing Supplier invoice detail route.
- Buyer payment: passed — payment details, virtual account actions, waiting status, and payment schedule navigation match the source.
- Responsive safety: passed — no horizontal overflow at 390 px and all primary controls remain visible.
- Browser console: passed — no errors or warnings in a fresh verification-page session.

## Investor dashboard and Treasury Agent decision

Source visual truth:

- Figma investor dashboard: `Gmn4FDxT8sXnW45RWWkgL1`, node `16:1055`.
- Figma Treasury Agent decision detail: `Gmn4FDxT8sXnW45RWWkgL1`, node `16:1150`.

Implementation captures:

- `.design-qa/implementation-investor-dashboard.jpg`
- `.design-qa/implementation-investor-agent-decision.jpg`

Comparison setup:

- Source frame: 1440 × 900 CSS px.
- Implementation viewport and capture: 1440 × 900 px at device scale factor 1.
- State: English, auto-invest active on the dashboard, investment completed on the decision detail.
- Full-view comparison: both source frames and both implementation captures were opened together in one comparison input.
- Focused region comparison: dashboard statistics/activity table and decision policy/execution cards were legible in the full-size comparison, so separate crops were not required.

Findings and iteration history:

- Initial P2 behavior issue: the RWA position action used an inert fragment when the current demo invoice had not yet reached the funded state.
- Fix: supplied the known demo Solana explorer transaction as a functional fallback while preserving the adapter-provided explorer URL when available.
- Post-fix evidence: the final browser snapshot exposes the full Solana explorer URL and the browser console contains no errors or warnings.
- Fonts and typography: passed — Inter/Arial hierarchy, weights, compact labels, and table density match the source.
- Spacing and layout rhythm: passed — 1280 × 800 shell, header/sidebar proportions, three-card grid, table, and decision columns align with the source. The language control intentionally occupies the leftmost position in the top-right control group.
- Colors and visual tokens: passed — violet investor states, neutral borders, pale sidebar, green PASS states, and blue transaction link match the source palette.
- Image quality and asset fidelity: passed — these screens contain no source raster imagery; the shared logo and avatar treatment remain consistent with the existing InvoiceX shell.
- Copy and content: passed — labels, values, policy checks, status chips, and transaction summary match the source. Korean equivalents are available through the shared language control.
- Responsive safety: passed — no horizontal page overflow at 390 px and both primary actions remain visible.
- Primary interactions: dashboard activity navigation, mandate navigation, Korean/English switching, and the RWA explorer action were verified.
- Automated checks: passed — lint, typecheck, 20 test files / 42 tests, and production build.

## Document-review refinement — 2026-08-18

Source visual truth:

- User-provided reference: `C:/Users/tjsvu/AppData/Local/Temp/codex-clipboard-3d544ef9-dc77-47b6-8c35-149bf8085bbb.png`.
- Target state: Korean supplier extraction review, desktop.

Implementation status:

- Updated `DocumentReviewSection` to use the same four document tabs as buyer verification, replacing the previous next/previous arrow controls.
- Replaced the disconnected three-step markers with a continuous 66.666% progress track matching the signup progress treatment.
- Unified the review heading with the shared Korean/system font stack and explicit inherited heading typography.
- Automated checks passed: `npm run typecheck`, `npm run test`, `npm run build`, and `npm run lint`.

Browser-rendered comparison:

- Blocked: the local app at `http://127.0.0.1:4173/supplier` remained in the loading state because its configured API did not return the invoice data. Consequently, the extraction-review route could not be captured, compared against the reference, or checked for browser-console errors in this run.
- No implementation screenshot was produced; the prior captures in this file predate this refinement and are not valid evidence for it.

Required fidelity surfaces:

- Fonts and typography: code-level update applied; browser evidence pending.
- Spacing and layout rhythm: code-level update applied; browser evidence pending.
- Colors and visual tokens: existing buyer-tab and signup-progress tokens reused; browser evidence pending.
- Image quality and asset fidelity: unchanged from the existing raster invoice preview.
- Copy and content: unchanged apart from retaining the existing document labels in the new tab control.

final result: blocked
