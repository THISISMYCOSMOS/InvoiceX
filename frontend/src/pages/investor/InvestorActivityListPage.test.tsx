import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { InvestorActivityListPage } from "./InvestorActivityListPage";

beforeEach(async () => {
  await scenarioAdapter.reset();
  await scenarioAdapter.analyzeInvoice("INV-2026-001");
  await scenarioAdapter.requestVerification("INV-2026-001");
  await scenarioAdapter.confirmVerification("VER-2026-001");
  await scenarioAdapter.respondToOffer("INV-2026-001", "ACCEPT");
});

test("lists Agent decisions and filters the visible result state", async () => {
  const user = userEvent.setup();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={queryClient}><MemoryRouter><InvestorActivityListPage /></MemoryRouter></QueryClientProvider>);

  expect(await screen.findByRole("heading", { name: "Agent Activity" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "INV-2026-001" })).toHaveAttribute("href", "/investor/activities/INV-2026-001");
  expect(screen.getAllByText("Under review")).toHaveLength(2);

  await user.click(screen.getByRole("button", { name: "Investment executed" }));
  expect(screen.getByText("No Agent decisions match this filter.")).toBeInTheDocument();
});
