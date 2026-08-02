import { expect, test } from "vitest";
import { DEMO_ANALYSIS, DEMO_DOCUMENTS, DEMO_INVOICE } from "../mocks/demoScenario";
import { deduplicateInvoicesBySourceReference, getInvoiceDisplayReference } from "./useInvoices";

test("keeps the latest retry for the same extracted invoice number", () => {
  const latest = {
    ...DEMO_INVOICE,
    id: "INV-2026-005",
    analysis: DEMO_ANALYSIS,
    documents: DEMO_DOCUMENTS,
  };
  const retry = {
    ...DEMO_INVOICE,
    id: "INV-2026-004",
    analysis: DEMO_ANALYSIS,
    documents: DEMO_DOCUMENTS,
  };

  expect(deduplicateInvoicesBySourceReference([latest, retry])).toEqual([latest]);
  expect(getInvoiceDisplayReference(latest)).toBe("INV-2026-001");
});
