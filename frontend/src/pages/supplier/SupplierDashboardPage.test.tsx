import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { SupplierDashboardPage } from "./SupplierDashboardPage";

beforeEach(async () => {
  await scenarioAdapter.reset();
});

function renderDashboard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SupplierDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("renders the Figma supplier dashboard summary and links each real invoice to its progress page", async () => {
  await scenarioAdapter.analyzeInvoice("INV-2026-001");
  await scenarioAdapter.requestVerification("INV-2026-001");
  renderDashboard();

  expect(await screen.findByRole("heading", { name: "Good morning, Minjun" })).toBeInTheDocument();
  expect(screen.getByText("USDC wallet balance")).toBeInTheDocument();
  expect(screen.getByText("In early settlement")).toBeInTheDocument();
  expect(screen.getByText("Waiting for buyer")).toBeInTheDocument();
  expect(screen.getByText("Settlement received")).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Recent invoices" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "New invoice" })).toHaveAttribute("href", "/supplier/invoices/new");
  expect(await screen.findByRole("link", { name: "View invoice INV-2026-001" })).toHaveAttribute("href", "/supplier/invoices/INV-2026-001");
  expect(screen.getByText("Buyer review")).toBeInTheDocument();
});
