import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, test } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { NewInvoicePage } from "./NewInvoicePage";

beforeEach(async () => {
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

  await user.click(screen.getByRole("button", { name: "Register demo invoice" }));

  expect(await screen.findByText("Invoice detail route")).toBeInTheDocument();
});
