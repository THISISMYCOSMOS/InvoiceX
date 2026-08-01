import { createMockAdapter } from "./mockAdapter";

test("progresses the demo invoice from analysis to settled", async () => {
  const adapter = createMockAdapter();

  await adapter.analyzeInvoice("INV-2026-001");
  await adapter.requestVerification("INV-2026-001");
  await adapter.confirmVerification("VER-2026-001");
  await adapter.respondToOffer(
    "INV-2026-001",
    "ACCEPT",
    "So11111111111111111111111111111111111111112",
  );
  await adapter.runFunding("INV-2026-001");
  await adapter.mockPayment("INV-2026-001");
  await adapter.runSettlement("INV-2026-001");

  const invoice = await adapter.getInvoice("INV-2026-001");

  expect(invoice.status).toBe("SETTLED");
  expect(invoice.supplier.walletAddress).toBe(
    "So11111111111111111111111111111111111111112",
  );
  expect(invoice.settlement?.investorSettlementUsdc).toBe(19_800);
});
