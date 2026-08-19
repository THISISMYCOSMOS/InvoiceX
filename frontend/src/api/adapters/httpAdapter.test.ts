import { vi } from "vitest";
import { createHttpAdapter } from "./httpAdapter";

test("uses the supplied v1 invoice list endpoint", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ items: [] }), { status: 200 }),
  );
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");

  await adapter.getInvoices();

  expect(fetchImpl).toHaveBeenCalledWith(
    "https://api.example.com/api/v1/invoices",
    expect.objectContaining({ method: "GET" }),
  );
});

test("submits document registration to the supplied v1 invoice endpoint", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ id: "INV-2026-001", status: "DOCUMENT_ANALYZING" }), { status: 200 }),
  );
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");
  const formData = new FormData();
  formData.append("INVOICE", new File(["pdf"], "invoice.pdf", { type: "application/pdf" }));

  await adapter.submitInvoiceDocuments(formData);

  expect(fetchImpl).toHaveBeenCalledWith(
    "https://api.example.com/api/v1/invoices",
    expect.objectContaining({ method: "POST", body: formData }),
  );
});

test("sends the connected supplier wallet with an accepted offer", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ invoice: { id: "INV-2026-001", status: "FUNDING" } }), { status: 200 }),
  );
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");

  await adapter.respondToOffer(
    "INV-2026-001",
    "ACCEPT",
    "So11111111111111111111111111111111111111112",
  );

  const request = fetchImpl.mock.calls[0][1] as RequestInit;
  expect(JSON.parse(request.body as string)).toEqual({
    response: "ACCEPT",
    supplierWalletAddress: "So11111111111111111111111111111111111111112",
  });
});

test("submits a Risk Score review request", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ invoice: { id: "INV-2026-001", status: "REVIEW_REQUESTED" } }), { status: 200 }),
  );
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");

  await adapter.requestRiskReview("INV-2026-001");

  expect(fetchImpl).toHaveBeenCalledWith(
    "https://api.example.com/api/v1/invoices/INV-2026-001/risk-review-request",
    expect.objectContaining({ method: "POST" }),
  );
});

test("shows the backend detail message for offer errors", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ message: "Solana 지갑을 연결해야 합니다." }), { status: 409 }),
  );
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");

  await expect(adapter.respondToOffer("INV-2026-001", "ACCEPT")).rejects.toThrow(
    "Solana 지갑을 연결해야 합니다.",
  );
});

test("prepares and confirms an investor wallet deposit", async () => {
  const preparation = {
    referenceId: "DEP-2026-001",
    investorWalletAddress: "Vote111111111111111111111111111111111111111",
    treasuryWalletAddress: "So11111111111111111111111111111111111111112",
    usdcMint: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
    amountUsdc: 20,
    decimals: 6,
    network: "SOLANA_DEVNET",
  };
  const fetchImpl = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(preparation), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({
      ...preparation,
      signature: "signature",
      status: "CONFIRMED",
      explorerUrl: "https://explorer.solana.com/tx/signature?cluster=devnet",
      confirmedAt: "2026-08-02T00:00:00Z",
    }), { status: 200 }));
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");

  await adapter.prepareInvestorDeposit(preparation.investorWalletAddress, 20);
  await adapter.confirmInvestorDeposit(preparation.referenceId, "signature");

  expect(fetchImpl.mock.calls[0][0]).toBe(
    "https://api.example.com/api/v1/investor/deposits/prepare",
  );
  expect(JSON.parse(fetchImpl.mock.calls[0][1]?.body as string)).toEqual({
    investorWalletAddress: preparation.investorWalletAddress,
    amountUsdc: 20,
  });
  expect(fetchImpl.mock.calls[1][0]).toBe(
    "https://api.example.com/api/v1/investor/deposits/confirm",
  );
  expect(JSON.parse(fetchImpl.mock.calls[1][1]?.body as string)).toEqual({
    referenceId: preparation.referenceId,
    signature: "signature",
  });
});
