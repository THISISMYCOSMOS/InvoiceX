import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { BuyerDashboardPage } from "./BuyerDashboardPage";

beforeEach(async () => {
  await scenarioAdapter.reset();
  await scenarioAdapter.analyzeInvoice("INV-2026-001");
  await scenarioAdapter.requestVerification("INV-2026-001");
});

test("renders the Figma buyer dashboard summary and verification table", async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BuyerDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByRole("heading", { name: "Invoice verification" })).toBeInTheDocument();
  expect(screen.getByText("New requests")).toBeInTheDocument();
  expect(screen.getByText("Due in 30 days")).toBeInTheDocument();
  expect(screen.getByText("Completed invoices")).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "New verification requests" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Review INV-2026-001" })).toHaveAttribute(
    "href",
    "/buyer/invoices/INV-2026-001?section=verification",
  );
  expect(screen.getByText("No payments are due right now.")).toBeInTheDocument();
});

test("shows confirmed invoices with a link to their details", async () => {
  await scenarioAdapter.confirmVerification("VER-2026-001");
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BuyerDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByRole("heading", { name: "Recently confirmed invoices" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View details for INV-2026-001" })).toHaveAttribute(
    "href",
    "/buyer/invoices/INV-2026-001?section=verification",
  );
});
