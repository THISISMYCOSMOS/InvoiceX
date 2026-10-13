import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, test } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { NewInvoicePage } from "./NewInvoicePage";

beforeEach(async () => {
  await scenarioAdapter.reset();
});

test("navigates to the returned invoice after uploading all required documents", async () => {
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

  const file = new File(["invoice"], "invoice.pdf", { type: "application/pdf" });
  await user.upload(screen.getByLabelText("Invoice file"), file);
  await user.upload(screen.getByLabelText("Contract file"), file);
  await user.upload(screen.getByLabelText("Purchase order file"), file);
  await user.upload(screen.getByLabelText("Proof of delivery file"), file);
  await user.click(screen.getByRole("button", { name: "Analyze documents" }));

  expect(await screen.findByText("Invoice detail route")).toBeInTheDocument();
});
