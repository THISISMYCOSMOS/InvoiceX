import { createMockAdapter } from "./mockAdapter";

test("progresses the demo invoice from analysis to settled", async () => {
  const adapter = createMockAdapter();

  await adapter.analyzeInvoice("INV-2026-001");
  await adapter.requestVerification("INV-2026-001");
  await adapter.confirmVerification("VER-2026-001");
  const supplierWalletAddress = "So11111111111111111111111111111111111111112";
  await adapter.respondToOffer("INV-2026-001", "ACCEPT", supplierWalletAddress);
  await adapter.runFunding("INV-2026-001");
  await adapter.mockPayment("INV-2026-001");
  await adapter.runSettlement("INV-2026-001");

  const invoice = await adapter.getInvoice("INV-2026-001");

  expect(invoice.status).toBe("SETTLED");
  expect(invoice.supplier.walletAddress).toBe(supplierWalletAddress);
  expect(invoice.settlement?.investorSettlementUsdc).toBe(19_800);
});

test("does not change the supplier wallet when an offer is declined", async () => {
  const adapter = createMockAdapter();
  const original = await adapter.getInvoice("INV-2026-001");

  await adapter.analyzeInvoice("INV-2026-001");
  await adapter.requestVerification("INV-2026-001");
  await adapter.confirmVerification("VER-2026-001");
  await adapter.respondToOffer(
    "INV-2026-001",
    "DECLINE",
    "So11111111111111111111111111111111111111112",
  );

  const declined = await adapter.getInvoice("INV-2026-001");
  expect(declined.supplier.walletAddress).toBe(original.supplier.walletAddress);
});
