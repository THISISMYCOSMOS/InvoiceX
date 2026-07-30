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
- Automated checks: passed — lint, typecheck, 17 test files / 34 tests, and production build.

## Language control addendum

- English remains the default language and the original Figma layout remains unchanged apart from the requested language control.
- Login: the control is the first child of the right panel, remains visible at desktop and mobile widths, and introduces no horizontal overflow.
- Application screens: the control is the first item in the shared top-right user group for Supplier, Buyer, and Investor routes.
- Persistence: switching to Korean updates the document language and survives route changes and a full reload.
- Localization: login, navigation, Supplier flow, Buyer flow, Investor flow, shared status/progress components, and developer demo controls render in both languages.
- Fresh browser session: passed with no console errors or warnings.
- Automated checks: passed — lint, typecheck, 17 test files / 34 tests, and production build.

final result: passed
