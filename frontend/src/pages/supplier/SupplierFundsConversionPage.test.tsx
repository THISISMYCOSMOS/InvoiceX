import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test } from "vitest";
import { SupplierFundsConversionPage } from "./SupplierFundsConversionPage";

function renderPage() {
  return render(
    <MemoryRouter>
      <SupplierFundsConversionPage />
    </MemoryRouter>,
  );
}

test("shows partner-only mock conversion flows without submitting a transaction", () => {
  renderPage();

  expect(screen.getByRole("heading", { name: "Funds conversion" })).toBeInTheDocument();
  expect(screen.getByText("Buy USDC", { selector: "h2" })).toBeInTheDocument();
  expect(screen.getByText("External partner")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /Withdraw USDC/i }));
  expect(screen.getByText("Current USDC balance")).toBeInTheDocument();
  expect(screen.getByText("3,240.50 USDC")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  expect(screen.getByRole("dialog")).toHaveTextContent("does not submit a payment");
});
