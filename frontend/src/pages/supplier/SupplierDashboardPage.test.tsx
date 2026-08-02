import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { SupplierDashboardPage } from "./SupplierDashboardPage";

vi.mock("../../hooks/useDevnetUsdcBalance", () => ({
  useDevnetUsdcBalance: () => ({
    address: "8xK2f7yZQmP8Y5BwL9Vx3dTs7cR2nJ6p91Q",
    balanceUsdc: 1.25,
    isLoading: false,
    isError: false,
  }),
}));

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

test("derives supplier dashboard statistics from actual invoice states and links each invoice to its progress page", async () => {
  await scenarioAdapter.analyzeInvoice("INV-2026-001");
  await scenarioAdapter.requestVerification("INV-2026-001");
  renderDashboard();

  expect(await screen.findByRole("heading", { name: "Good morning, Minjun" })).toBeInTheDocument();
  expect(screen.getByText("USDC wallet balance")).toBeInTheDocument();
  expect(screen.getByText("In early settlement")).toBeInTheDocument();
  expect(screen.getByText("Waiting for buyer")).toBeInTheDocument();
  expect(screen.getByText("Settlement received")).toBeInTheDocument();
  expect(within(screen.getByLabelText("USDC wallet balance")).getByText("1.25")).toBeInTheDocument();
  expect(within(screen.getByLabelText("USDC wallet balance")).getByText("Connected wallet")).toBeInTheDocument();
  expect(within(screen.getByLabelText("In early settlement")).getByText("0")).toBeInTheDocument();
  expect(within(screen.getByLabelText("Waiting for buyer")).getByText("1")).toBeInTheDocument();
  expect(within(screen.getByLabelText("Settlement received")).getByText("0")).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Recent invoices" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "New invoice" })).toHaveAttribute("href", "/supplier/invoices/new");
  expect(await screen.findByRole("link", { name: "View invoice INV-2026-001" })).toHaveAttribute("href", "/supplier/invoices/INV-2026-001");
  expect(screen.getByText("Buyer review")).toBeInTheDocument();
});
