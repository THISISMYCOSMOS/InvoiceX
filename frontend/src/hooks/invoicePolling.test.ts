import { describe, expect, it } from "vitest";
import { getInvoicePollingInterval } from "./invoicePolling";

describe("getInvoicePollingInterval", () => {
  it("keeps refetching while a backend workflow is still processing", () => {
    expect(getInvoicePollingInterval("RWA_ISSUED")).toBe(2_000);
    expect(getInvoicePollingInterval("FUNDING")).toBe(2_000);
  });

  it("stops refetching once the invoice reaches a stable state", () => {
    expect(getInvoicePollingInterval("FUNDED")).toBe(false);
    expect(getInvoicePollingInterval("SETTLED")).toBe(false);
  });
});
