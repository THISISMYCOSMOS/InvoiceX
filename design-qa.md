# Supplier dashboard navigation and notification update — QA

## Comparison target

- Source visual truth: `C:/Users/tjsvu/AppData/Local/Temp/codex-clipboard-192338fd-e691-4200-8614-c7bdb2d2313e.png`
- Implementation: supplier dashboard at `http://localhost:5173/supplier`
- Source pixels: 1919 × 942.
- Implementation viewport: 1421 × 912 CSS pixels at device pixel ratio 1.
- State: Korean supplier dashboard, no registered invoice, notification panel closed.
- Density normalization: not required; both captures were evaluated at CSS-pixel density.

## Evidence checked

- Full view: rendered browser capture confirms the existing centered shell, top bar, left navigation, dashboard cards, and recent-invoice empty state remain intact.
- Focused regions: the top-right action area confirms the log-out text has been replaced with the bell control; the left navigation confirms `대시보드`, `인보이스 등록`, and `프로필` copy. The profile route confirms the new log-out section is visible.
- Primary interactions: opening the bell displays the empty notification state, and profile navigation exposes the new log-out control. The bell closes automatically on route navigation.

## Required fidelity surfaces

- Fonts and typography: existing Inter-based typography, hierarchy, and compact header sizing are preserved.
- Spacing and layout rhythm: the bell keeps the original 28px header-control footprint; the sidebar retains its prior vertical rhythm. The notification popover is anchored below the bell and does not alter the header layout.
- Colors and visual tokens: existing slate, blue, green, and red semantic tokens are used. The profile log-out section uses a contained low-emphasis danger treatment.
- Image quality and asset fidelity: no image-bearing UI was changed. Existing brand assets remain unchanged; Phosphor icons are used for new controls.
- Copy and content: the greeting now consumes the authenticated onboarding contact name; navigation and notification text match the requested Korean terminology.

## Findings

- No actionable P0, P1, or P2 visual issues found for the requested changes.
- [P3] Completed notifications are data-driven, so an empty invoice list correctly shows an empty state. The two requested completion messages appear when the matching invoice statuses exist.

## Implementation checklist

- [x] Use onboarding contact name in supplier greeting.
- [x] Rename supplier navigation labels.
- [x] Replace header log-out with an interactive notification control.
- [x] Show invoice-review and early-settlement completion notifications from invoice state.
- [x] Add profile log-out control.
- [x] Verify typecheck, tests, lint, and local browser interactions.

## Comparison history

1. Initial implementation revealed that the notification popover could remain open after route navigation.
   - Fix: close it whenever `pathname` changes.
   - Post-fix evidence: profile navigation no longer keeps the notification panel open.

## Invoice registration progress consistency — QA

### Comparison target

- Source visual truth: the existing `2 / 3 추출 정보 확인` progress treatment on `http://localhost:5173/supplier/invoices/INV-2026-004`.
- Implementation captures: `F:/De-Butler/InvoiceX/.codex-stage-1.png`, `F:/De-Butler/InvoiceX/.codex-stage-2.png`, and `F:/De-Butler/InvoiceX/.codex-stage-3.png`.
- Viewport: 1421 × 912 CSS pixels for all three states.
- States: initial document upload, extraction review, and buyer review requested.

### Evidence checked

- Full view: the three browser captures preserve the existing InvoiceX shell, navigation, typography, spacing, and page-specific content.
- Focused region: all three pages render the shared `.review-progress` component with the same 29.5px height and identical label hierarchy.
- Progress values: stage 1 fills 330.33px of 991px, stage 2 fills 660.66px of 991px, and stage 3 fills the full 950px available in its workflow container.
- Primary interaction: no new interaction was introduced; direct route checks confirmed the correct step state for each workflow status.
- Browser diagnostics: no console errors were reported after visiting all three states.

### Required fidelity surfaces

- Fonts and typography: the existing progress summary typography is reused unchanged.
- Spacing and layout rhythm: the shared component keeps the same summary-to-track spacing on every screen and respects each page container width.
- Colors and visual tokens: the existing cyan-to-violet progress gradient and slate track are reused.
- Image quality and asset fidelity: no image assets were added or modified.
- Copy and content: the visible steps are `1 / 3 문서 업로드`, `2 / 3 추출 정보 확인`, and `3 / 3 구매기업 검토 요청`.

### Findings

- No actionable P0, P1, or P2 visual issues found for the requested progress-state unification.
- Follow-up width check: the buyer-review card and the `3 / 3` progress bar now share the same 950px rendered width and x-position at the 1421 × 912 viewport.

### Implementation checklist

- [x] Add the progress treatment to the initial upload screen.
- [x] Reuse the same component on extraction review.
- [x] Replace the disconnected buyer-review status list with the `3 / 3` treatment.
- [x] Verify targeted tests, TypeScript compilation, browser rendering, and console output.

final result: passed

---

# Supplier Risk Passport / early-settlement / RWA flow — QA

## Comparison target

- Source visual truth: the supplier invoice lifecycle screenshot attached to the current browser comment.
- Product specification: `C:/Users/tjsvu/.codex/attachments/3bc43ac0-2c62-47ce-a9e4-c623cbf66bd1/pasted-text.txt`.
- Implementation: `http://localhost:5173/supplier/invoices/INV-2026-005`.
- Implementation viewport: 1421 × 912 CSS pixels at device pixel ratio 1.
- State: authenticated Supplier, invoice `INV-2026-005`, buyer confirmation complete, RWA offer ready.
- Density normalization: not required; the source browser evidence and implementation were evaluated at the same CSS-pixel viewport.

## Evidence checked

- Full-view Risk Passport capture: `F:/De-Butler/InvoiceX/.codex-artifacts/risk-passport-stage-v2.png`.
- Full-view early-settlement terms capture: `F:/De-Butler/InvoiceX/.codex-artifacts/settlement-terms-stage-v2.png`.
- Full-view final RWA issuance capture: `F:/De-Butler/InvoiceX/.codex-artifacts/rwa-issuance-stage.png`.
- Focused regions: signup-style lifecycle progress, score/data-coverage panel, sourced factor rows, Discount/Reserve breakdown, and final issuance summary.

## Interaction verification

- [x] Risk Passport → early-settlement terms.
- [x] Early-settlement terms → Risk Passport (back navigation).
- [x] Early-settlement terms → final RWA issuance review.
- [x] Final RWA issuance review → early-settlement terms (back navigation).
- [x] Progress changes from `3 / 7` to `4 / 7` to `5 / 7` with the corresponding stage.
- [x] Browser console contains no errors during the verified flow.
- [x] Final RWA issuance mutation was intentionally not executed in browser QA; its handler and request flow are covered by component and route tests.

## Findings history

### Iteration 1

- P2: previously persisted Risk Passport records did not contain the newly introduced face-value/terms fields, which made the terms view unavailable. Resolved with a currency-safe legacy derivation that preserves the existing 94% advance policy.
- P2: the Risk Passport score sat inline with the card content and weakened hierarchy. Resolved by stacking and vertically centering the score block.

### Iteration 2

- No actionable P0, P1, or P2 visual issues found.
- Signup-style single-stage progress is consistent across Risk Passport, terms, and issuance review.
- Discount and Reserve are visually and semantically separated, while the final RWA amount remains equal to the existing initial advance amount.

## Verification checklist

- [x] Backend focused tests: 11 passed.
- [x] Backend full regression: passed.
- [x] Frontend targeted route/component tests: 34 passed.
- [x] Changed frontend files: ESLint passed.
- [x] Frontend TypeScript compilation: passed.
- [x] `git diff --check`: no whitespace errors (line-ending warnings only).

final result: passed

---

# Supplier company-profile editing — QA

## Comparison target

- Source visual truth: `browser:` capture from User Comment 1 on `http://localhost:5173/supplier/company-wallet` at 1421 × 912.
- Implementation route: `http://localhost:5173/supplier/company-wallet`.
- Read-state screenshot: `F:/De-Butler/InvoiceX/.codex-artifacts/company-profile-read.png`.
- Edit-state screenshot: `F:/De-Butler/InvoiceX/.codex-artifacts/company-profile-edit.png`.
- Source and implementation size: 1421 × 912 pixels; CSS viewport 1421 × 912 at device pixel ratio 1.
- Density normalization: not required.
- State: authenticated Korean Supplier with an existing embedded settlement wallet and an invalid legacy eight-digit registration number.

## Full-view and focused comparison

- Full view preserves the source app shell, two-column company/wallet grid, card radii, border tokens, navigation, logout, and account-deletion sections.
- Focused company-card comparison confirms the new `정보 수정` affordance fits the existing header without changing card hierarchy.
- Focused edit-state comparison confirms six fields use the existing input height, blue focus token, two-column rhythm, and responsive one-column fallback.
- No image assets were added or replaced; existing Phosphor icons remain sharp and consistent.

## Required fidelity surfaces

- Typography: existing family, weights, small-label hierarchy, and truncation behavior retained.
- Spacing/layout: profile and wallet cards remain aligned; edit controls use the source 8–10px radius and compact density.
- Colors/tokens: existing blue action, green verification, neutral read-only, and red validation tokens reused.
- Image quality/assets: no raster or custom illustration changes; the existing icon library is reused.
- Copy/content: editable fields are clearly separated from immutable email, country code, and account role.

## Findings history

### Iteration 1

- P2: the source screen exposed company information as read-only, blocking demo correction of invalid legacy registration data. Fixed with an explicit header edit action and inline edit mode.
- P2: country code, email, and role could be mistaken for editable identity fields. Fixed by presenting country as read-only and grouping email/role in a neutral immutable-information panel.

### Iteration 2

- No actionable P0, P1, or P2 visual issues remain.
- The invalid legacy registration number now produces a clear inline ten-digit validation message before any API request.

## Interaction and engineering verification

- [x] Open company-information edit mode.
- [x] Verify current company/representative values populate the form.
- [x] Verify invalid Korean registration number is blocked client-side.
- [x] Cancel editing and return to the read state.
- [x] Verify save request, response synchronization, and success state with synthetic component data.
- [x] Verify database persistence by saving and reloading through `/api/v1/auth/me` in backend tests.
- [x] Browser console errors: none.
- [x] Frontend full regression: 31 files / 95 tests passed.
- [x] Frontend full ESLint and TypeScript checks passed.
- [x] Backend full regression passed after updating the OpenAPI contract.
- [x] `git diff --check`: no whitespace errors (line-ending warnings only).

final result: passed
