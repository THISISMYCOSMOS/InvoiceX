import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { InvestorDashboardPage } from "./InvestorDashboardPage";

beforeEach(async () => {
  await scenarioAdapter.reset();
  await scenarioAdapter.analyzeInvoice("INV-2026-001");
  await scenarioAdapter.requestVerification("INV-2026-001");
  await scenarioAdapter.confirmVerification("VER-2026-001");
  await scenarioAdapter.respondToOffer("INV-2026-001", "ACCEPT");
});

test("renders the investor dashboard from the investor dashboard design", async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <InvestorDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  expect(screen.getByText("312,400")).toBeInTheDocument();
  expect(screen.getByText("Total profit")).toBeInTheDocument();
  expect(screen.getByText("Auto-invested RWA")).toBeInTheDocument();
  expect(screen.getByText("Overdue receivables")).toBeInTheDocument();
  expect(screen.getByText("Auto-invest active · Mandate active")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Manage Investment Policy" })).toHaveAttribute(
    "href",
    "/investor/investment-policy",
  );
  expect(await screen.findByText("Under review")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View all Agent Activity" })).toHaveAttribute(
    "href",
    "/investor/activities",
  );
  expect(screen.getByRole("link", { name: "INV-2026-001" })).toHaveAttribute(
    "href",
    "/investor/activities/INV-2026-001",
  );
  expect(screen.queryByRole("button", { name: "Purchase RWA" })).not.toBeInTheDocument();
});
