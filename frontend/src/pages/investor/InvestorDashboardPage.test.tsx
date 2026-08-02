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

test("renders the treasury overview from the investor dashboard design", async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <InvestorDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByRole("heading", { name: "Treasury overview" })).toBeInTheDocument();
  expect(screen.getByText("312,400")).toBeInTheDocument();
  expect(screen.getByText("187,600")).toBeInTheDocument();
  expect(screen.getByText("72,840")).toBeInTheDocument();
  expect(screen.getByText("Needs attention")).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getByText("Auto-invest active · Mandate active")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Manage mandate" })).toHaveAttribute(
    "href",
    "/investor/setup",
  );
  expect(await screen.findByText("No investment has been executed yet.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Purchase RWA" })).not.toBeInTheDocument();
});
