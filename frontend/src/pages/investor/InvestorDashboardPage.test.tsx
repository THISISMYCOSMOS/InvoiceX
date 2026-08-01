import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  const user = userEvent.setup();
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
  expect(screen.getByRole("link", { name: "Manage mandate" })).toHaveAttribute(
    "href",
    "/investor/setup",
  );
  expect(await screen.findByRole("link", { name: "INV-2026-001" })).toHaveAttribute(
    "href",
    "/investor/activities/INV-2026-001",
  );
  await user.click(screen.getByRole("button", { name: "Purchase RWA" }));
  expect(await screen.findByText("There are no issued RWAs awaiting investment.")).toBeInTheDocument();
});
