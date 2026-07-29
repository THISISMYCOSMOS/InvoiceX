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
