# Design QA

- Source visual truth: Browser annotation screenshots and the captured Supplier dashboard at `http://127.0.0.1:4173/supplier`.
- Implementation: `http://127.0.0.1:4173/supplier/company-wallet`.
- Viewport: 1402 × 794 CSS px.
- Source pixels: 1402 × 794, device pixel ratio 1.
- Implementation pixels: 1402 × 794, device pixel ratio 1.
- Density normalization: Not required; both captures use the same browser, viewport, and density.
- State: Korean locale, Supplier role, settlement wallet connected.

## Full-view comparison evidence

The source dashboard and implementation were captured in the same in-app browser and emitted together for direct comparison. The implementation preserves the existing 64 px header, 200 px Supplier sidebar, main-content padding, blue Supplier accent, white bordered cards, typography hierarchy, and compact information density.

## Focused region comparison evidence

- Header: brand, role switcher, language toggle, avatar, and company name retain the source order and spacing. The Supplier wallet label is intentionally removed per annotation.
- Sidebar: `회사 및 지갑` uses the same link dimensions, active blue treatment, radius, type size, and alignment as `개요`.
- Content: company and wallet cards reuse the dashboard border, radius, muted label color, blue/green semantic states, and spacing rhythm. Text and controls remain fully visible without horizontal overflow.

## Required fidelity surfaces

- Fonts and typography: Existing Inter stack, weights, compact labels, heading hierarchy, and line heights are preserved.
- Spacing and layout rhythm: Page heading, 24 px section gap, 16 px card gap, card headers, and internal field spacing align with the Supplier dashboard rhythm.
- Colors and visual tokens: Existing navy text, slate secondary text, blue Supplier accents, green verification states, and neutral borders are reused.
- Image quality and asset fidelity: No raster imagery is required. All functional icons use the existing Phosphor icon library; no custom SVG or placeholder artwork was introduced.
- Copy and content: Company verification, public wallet address, network, balance, connection state, and security copy support the requested company-and-wallet task in both English and Korean.

## Interaction verification

- Supplier sidebar link navigates to the new page and receives the correct active state.
- Wallet disconnect reveals the empty connection state.
- Wallet connect restores the address, metrics, and connected status.
- Role and language controls remain available.
- Browser console errors: none.
- Horizontal overflow: none at the captured desktop viewport.

## Findings

No actionable P0, P1, or P2 visual or interaction issues were found.

## Comparison history

- Initial comparison: passed with no P0/P1/P2 findings; no corrective visual iteration was required.

## Follow-up polish

- P3: A future real-wallet integration may replace the demo timestamp and connection state with provider data.

## Buyer verification annotation QA

- Source visual truth: Browser annotation on `http://127.0.0.1:4173/buyer/invoices/INV-2026-001?section=verification`.
- Implementation: Same route with the new top-left back control.
- Viewport and density: 1402 × 794 CSS px, device pixel ratio 1.
- State: Korean locale, Buyer verification request.
- Full-view evidence: The control sits above the breadcrumb and heading without shifting the two-column verification grid or introducing horizontal overflow.
- Focused evidence: The 28 px control uses the existing neutral border, compact type, 7 px radius, Phosphor arrow icon, and green Buyer hover/focus treatment.
- Primary interaction: Selecting `뒤로 가기` navigates to `/buyer`; verified in the in-app browser.
- Browser console errors: none.
- Findings: No actionable P0, P1, or P2 issues.

## Buyer payment queue annotation QA

- Source visual truth: Browser annotation on `http://127.0.0.1:4173/buyer`.
- Implementation: Same route with the new `결제 필요` queue below `새 확인 요청`.
- Viewport and density: 1402 × 794 CSS px, device pixel ratio 1.
- State: Korean locale, Buyer dashboard, one priority payment.
- Full-view evidence: The new card follows the existing table width, border, radius, header height, column rhythm, and Buyer green action treatment. Both queues remain visible above the fold without horizontal overflow.
- Focused evidence: The amber priority and remaining-day pills provide a distinct due-date signal without competing with the green primary action.
- Primary interaction: Selecting `결제하기` navigates to `/buyer/invoices/INV-2026-001?section=payment` and renders the maturity-payment screen.
- Browser console errors: none.
- Findings: No actionable P0, P1, or P2 issues.

## Buyer payment navigation annotation QA

- Source visual truth: Browser annotation on the Buyer maturity-payment screen.
- Implementation: The inactive `완료` item is removed; the sidebar now contains only `개요`, `확인 요청`, and `결제 일정`.
- State and viewport: Korean locale, payment schedule active, 1402 × 794 CSS px at device pixel ratio 1.
- Evidence: Active navigation styling and sidebar spacing remain unchanged, with no overflow or console errors.
- Findings: No actionable P0, P1, or P2 issues.

## Investor topbar annotation QA

- Source visual truth: Browser annotation on `http://127.0.0.1:4173/investor`.
- Implementation: The `Vault · 7VB...0Qe` label is removed from the topbar.
- State and viewport: Korean locale, Investor dashboard, 1402 × 794 CSS px at device pixel ratio 1.
- Evidence: Role switcher, language toggle, auto-invest status, avatar, and company name remain aligned without overflow or console errors.
- Findings: No actionable P0, P1, or P2 issues.

final result: passed

## Company sign-up flow QA — 2026-08-18

- Source visual truth: Figma nodes `123:1104`, `123:1143`, `123:1191`, `123:1252`, and `123:1302` from `https://www.figma.com/design/Gmn4FDxT8sXnW45RWWkgL1/GxS`.
- Implementation: browser-rendered `http://127.0.0.1:5173/signup` (email entry, code, role, company details, and completion states).
- Viewport: 1440 × 900 CSS px, device pixel ratio 1; comparison focused on the centered 1280 × 800 application shell.
- Source and implementation pixels: Figma source frame 1280 × 800; implementation browser capture 1440 × 900 with the same 1280 × 800 shell at native CSS size. No density scaling was applied.
- State: Korean sign-up flow; verification used mock inputs only (`finance@company.com`, six-digit code, Investor role, dummy company information).

### Full-view comparison evidence

The Figma email-entry capture and the browser-rendered email-entry capture were opened together in the same visual QA pass. The split layout, 480 px gradient brand panel, 800 px form panel, header actions, 560/640 px content widths, progress treatment, form controls, and primary CTA were compared at the desktop shell size. The remaining four Figma states were also checked against their corresponding interactive implementation states.

### Focused region comparison evidence

- Email and code states: Input heights, six-cell OTP layout, timer/re-send row, CTA, and alternate-email action match the target structure.
- Company-role state: The completion toast, Supplier/Buyer/Investor card hierarchy, semantic role rails, selected radio state, and 2/3 progress state are present.
- Company-details and completion states: The two-column form, verified-email strip, completion summary, activation chip, and role-aware dashboard CTA match the Figma composition.

### Required fidelity surfaces

- Fonts and typography: The existing Inter stack is used with matching bold display headings, compact labels, muted helper copy, and Korean line wrapping.
- Spacing and layout rhythm: The desktop 1280 × 800 shell preserves the Figma panel split, panel padding, content widths, 50 px CTA height, 76 px role rows, and form grid rhythm.
- Colors and visual tokens: The navy-to-violet brand panel, cyan/blue/violet progress fill, blue primary actions, pale verification banner, neutral borders, and role accents follow the source.
- Image quality and asset fidelity: The source contains no raster imagery or custom icon assets. The wordmark and UI controls remain text/CSS interface elements, with no placeholder artwork introduced.
- Copy and content: Figma Korean labels and supporting copy are preserved. Completion values reflect the locally entered mock data.

### Interaction verification

- Login's `Create a company account` link routes to `/signup`.
- Email submission advances to OTP; six code fields accept digits and advance focus; resend clears the fields; alternate-email returns to the first state.
- Role selection supports all three roles and the selected role routes the completion CTA to its corresponding dashboard.
- Company details submission renders the completion card; the tested Investor flow navigated to `/investor`.
- The top-left action routes only the email-entry screen to `/login`; each later state returns to its immediately preceding sign-up state, including completion back to company details.
- Browser console errors: none.

### Findings

No actionable P0, P1, or P2 visual or interaction mismatches were found.

### Comparison history

- Initial comparison: the selected role control showed the browser's default dark focus outline. The component style was updated to use the intended blue focus treatment.
- Post-fix comparison: no actionable P0, P1, or P2 findings remain.

### Follow-up polish

- P3: The company-information progress text deliberately remains `1 / 3 기업 이메일 인증` to match the provided Figma node, despite its fully filled progress bar.

final result: passed
