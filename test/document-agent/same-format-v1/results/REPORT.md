# InvoiceX Document Agent scenario evaluation

- Source: `origin/main` at `9298e1feb3d1894a9e86808277b86c64c2d2e01f`
- Model: `gemini-3.6-flash`
- Run date: 2026-08-12 KST
- Isolation: detached Git worktree; the user's checkout was not modified

## Deterministic baseline

- Pytest: 52 passed, 0 failed
- Ruff: passed
- Existing real Gemini golden sets: 2/2 exact pass

## Scenario coverage

- Designed: 19 sets, 76 PDFs
- Measured with a structured Gemini result: 11 sets, 44 PDFs
- Not measured because the free API returned HTTP 429: 8 sets, 32 PDFs

## Accuracy conditional on a structured result

- Exact set pass rate: 11/11 (100%)
- Document type accuracy: 44/44 (100%)
- Field-cell accuracy including expected nulls: 616/616 (100%)
- Populated-field accuracy: 451/451 (100%)
- Mismatch field TP/FP/FN: 11/0/0
- Mismatch precision/recall/F1: 100% / 100% / 100%
- Review decision accuracy: 11/11 (100%)
- Normal-set false positives: 0/3 (0%)

These percentages describe only the 11 sets that returned a structured analysis. They do not
represent all 19 designed sets.

## Passed sets

- Existing: happy path; amount plus unit-price mismatch
- Normalization: equivalent number formats; equivalent date format
- Single mismatch: total amount; unit price; quantity; supplier; buyer; purchase-order number
- Multiple mismatch: buyer, currency, and quantity together

## Not yet measured

- Identifier separator spacing
- Single currency mismatch
- Single item-name mismatch
- Single contract-number mismatch
- Delivery-completed mismatch
- Linked amount and unit-price mismatch in the expanded fixture
- Four distinct unit prices
- Errors located in separate documents

Every unmeasured set ended before content analysis with `AI_TEMPORARILY_UNAVAILABLE`, HTTP 429.
They are not counted as Document Agent content failures.

## Remaining measurement

Repeatability remains unmeasured. The approved target is 10 runs per set, but only one successful
run per measured set was completed before the free API quota was exhausted.
