import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { InvestorDashboardPage } from "./InvestorDashboardPage";

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
  expect(screen.getByRole("link", { name: "Manage mandate" })).toHaveAttribute(
    "href",
    "/investor/setup",
  );
  expect(screen.getByRole("link", { name: "INV-2026-001" })).toHaveAttribute(
    "href",
    "/investor/activities/INV-2026-001",
  );
});
