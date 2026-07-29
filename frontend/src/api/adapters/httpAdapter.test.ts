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
