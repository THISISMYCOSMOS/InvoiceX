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

test("shows the backend detail message for offer errors", async () => {
  const fetchImpl = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ message: "Solana 지갑을 연결해야 합니다." }), { status: 409 }),
  );
  const adapter = createHttpAdapter(fetchImpl, "https://api.example.com/api/v1");

  await expect(adapter.respondToOffer("INV-2026-001", "ACCEPT")).rejects.toThrow(
    "Solana 지갑을 연결해야 합니다.",
  );
});
