# Document Agent actual public-form evaluation

Date: 2026-08-13 KST

## Scope

- Current Document Agent and configured `gemini-3.6-flash`; no agent model, prompt, or production code changes.
- Eight calls total, one call per public original form layout, with no automatic retries.
- Minimum API-call start interval: 40 seconds.
- Synthetic transaction values were placed into public original layouts so exact ground truth remained known.
- This suite measures document type classification and field extraction. It does not measure cross-document mismatch detection or fraud detection.

## Sources

1. Adobe Proforma Invoice Template
2. GSA Form 3708 Invoice
3. GSA Form 300 Order for Supplies and Services
4. Optional Form 348 Order Schedule Continuation
5. Standard Form 26 Award/Contract
6. Standard Form 1449 Solicitation/Contract/Order
7. GSA Form 3025 Receiving Report
8. GSA Form 1678 Status Report of Orders and Shipments

Exact URLs and source/filled SHA-256 hashes are recorded in `../../pdf/document-agent-real-public-v1/source-manifest.json`.

## Measured results

| Metric | Result |
| --- | ---: |
| API calls attempted | 8 |
| Valid structured results | 6/8 (75.0%) |
| API/response failures | 2/8 (25.0%) |
| Exact cases among all attempts | 5/8 (62.5%) |
| Exact cases among valid results | 5/6 (83.3%) |
| Populated field values among valid results | 63/63 (100.0%) |
| Null field values among valid results | 21/21 (100.0%) |
| All field values among valid results | 84/84 (100.0%) |
| Missing-field membership among valid results | 84/84 (100.0%) |
| Document type exact under the predeclared labels | 5/6 (83.3%) |

## Per-case outcome

| Case | Outcome |
| --- | --- |
| Adobe proforma invoice | Exact |
| GSA 3708 invoice | Exact |
| GSA 300 purchase order | Exact |
| OF 348 purchase order | No result: HTTP 503, no retry |
| SF 26 award/contract | Exact |
| SF 1449 solicitation/contract/order | All 14 field/null decisions exact; classified as `PURCHASE_ORDER` instead of the predeclared `CONTRACT` label |
| GSA 3025 receiving report | No result: Gemini response failed schema validation, no retry |
| GSA 1678 order/shipment report | Exact |

## Interpretation

The field extraction result is strong for returned responses: every populated value and every expected null was exact. End-to-end availability was weaker: two of eight calls did not yield a usable result. The single type-label disagreement is genuinely ambiguous because the official SF 1449 title and FAR usage explicitly combine solicitation, contract, and order functions. Therefore the strict predeclared-label score is reported unchanged, but it should not be described as a clear semantic misclassification without a separate multi-label or primary-use labeling policy.

No claim is made about detecting fabricated facts. This test only verifies extraction from visible document content and type classification.
