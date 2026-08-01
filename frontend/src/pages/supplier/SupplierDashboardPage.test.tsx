import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, test, vi } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { DEMO_INVOICE } from "../../mocks/demoScenario";
import { SupplierDashboardPage } from "./SupplierDashboardPage";

beforeEach(async () => {
  await scenarioAdapter.reset();
});

afterEach(() => {
  vi.restoreAllMocks();
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

test("every registered invoice opens, not just the first row", async () => {
  vi.spyOn(scenarioAdapter, "getInvoices").mockResolvedValue([
    { ...DEMO_INVOICE, id: "INV-2026-001", status: "OFFER_READY" },
    { ...DEMO_INVOICE, id: "INV-2026-002", status: "ERROR" },
    { ...DEMO_INVOICE, id: "INV-2026-003", status: "SETTLED" },
  ]);

  renderDashboard();

  for (const id of ["INV-2026-001", "INV-2026-002", "INV-2026-003"]) {
    expect(await screen.findByRole("link", { name: `View invoice ${id}` })).toHaveAttribute(
      "href",
      `/supplier/invoices/${id}`,
    );
  }
});

test("renders the Figma supplier dashboard summary and invoice table", async () => {
  renderDashboard();

  expect(await screen.findByRole("heading", { name: "Good morning, Minjun" })).toBeInTheDocument();
  expect(screen.getByText("USDC wallet balance")).toBeInTheDocument();
  expect(screen.getByText("In early settlement")).toBeInTheDocument();
  expect(screen.getByText("Waiting for buyer")).toBeInTheDocument();
  expect(screen.getByText("Early settlement received")).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Recent invoices" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "New invoice" })).toHaveAttribute("href", "/supplier/invoices/new");
});
