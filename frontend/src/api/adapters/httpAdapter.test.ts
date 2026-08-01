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

test("forwards the connected supplier wallet when accepting an offer", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ id: "INV-2026-001", status: "FUNDING" }), { status: 200 }),
  );
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");
  const supplierWalletAddress = "So11111111111111111111111111111111111111112";

  await adapter.respondToOffer("INV-2026-001", "ACCEPT", supplierWalletAddress);

  expect(fetchImpl).toHaveBeenCalledWith(
    "https://api.example.com/api/v1/invoices/INV-2026-001/offer-response",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ response: "ACCEPT", supplierWalletAddress }),
    }),
  );
});

test("exposes the backend message instead of raw JSON on an offer error", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ message: "Connect a valid Solana wallet." }), { status: 409 }),
  );
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");

  await expect(adapter.respondToOffer("INV-2026-001", "ACCEPT")).rejects.toThrow(
    "Connect a valid Solana wallet.",
  );
});
