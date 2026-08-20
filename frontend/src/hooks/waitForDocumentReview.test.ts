import { expect, test, vi } from "vitest";
import { DEMO_INVOICE } from "../mocks/demoScenario";
import { waitForDocumentReview } from "./waitForDocumentReview";

test("waits for the uploaded invoice to reach document review without a dashboard visit", async () => {
  const getInvoice = vi.fn()
    .mockResolvedValueOnce({ ...DEMO_INVOICE, status: "DOCUMENT_ANALYZING" })
    .mockResolvedValueOnce({ ...DEMO_INVOICE, status: "DOCUMENT_REVIEW_REQUIRED" });

  const reviewed = await waitForDocumentReview(
    { ...DEMO_INVOICE, status: "DOCUMENT_ANALYZING" },
    getInvoice,
    { intervalMs: 0, timeoutMs: 1_000 },
  );

  expect(reviewed.status).toBe("DOCUMENT_REVIEW_REQUIRED");
  expect(getInvoice).toHaveBeenCalledTimes(2);
});

test("surfaces an analysis failure instead of navigating away", async () => {
  await expect(waitForDocumentReview(
    { ...DEMO_INVOICE, status: "ERROR" },
    vi.fn(),
    { intervalMs: 0, timeoutMs: 1_000 },
  )).rejects.toThrow("문서 분석을 완료하지 못했습니다");
});
