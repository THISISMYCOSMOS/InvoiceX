import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { NewInvoicePage } from "./NewInvoicePage";

beforeEach(async () => {
  vi.restoreAllMocks();
  await scenarioAdapter.reset();
});

test("navigates to the returned invoice from the mock quick-registration action", async () => {
  const user = userEvent.setup();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/supplier/invoices/new"]}>
        <Routes>
          <Route path="/supplier/invoices/new" element={<NewInvoicePage />} />
          <Route path="/supplier/invoices/:invoiceId" element={<p>Invoice detail route</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(screen.getByText("1 / 3 Upload documents")).toHaveAttribute("aria-current", "step");

  await user.click(screen.getByRole("button", { name: "Register demo invoice" }));

  expect(await screen.findByText("Invoice detail route")).toBeInTheDocument();
});

test("replaces the registration form with a large analysis state while documents are processing", async () => {
  const user = userEvent.setup();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  vi.spyOn(scenarioAdapter, "submitInvoiceDocuments").mockImplementation(() => new Promise(() => undefined));

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/supplier/invoices/new"]}>
        <NewInvoicePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  await user.click(screen.getByRole("button", { name: "Register demo invoice" }));

  expect(await screen.findByRole("heading", { name: "Identifying your invoice documents" })).toBeInTheDocument();
  expect(screen.getByRole("progressbar", { name: "Document analysis in progress" })).not.toHaveAttribute("aria-valuenow");
  expect(screen.getByText("Identifying documents and extracting fields")).toHaveAttribute("aria-current", "step");
  expect(screen.queryByText("DOCUMENT AGENT")).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Register a new invoice" })).not.toBeInTheDocument();
});
