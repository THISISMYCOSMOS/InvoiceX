import { render, screen } from "@testing-library/react";
import { DEMO_INVOICE } from "../../mocks/demoScenario";
import { BuyerInvoiceDetailContent } from "./BuyerInvoiceDetailPage";

test("shows verification controls for a buyer-review invoice", () => {
  render(<BuyerInvoiceDetailContent invoice={{ ...DEMO_INVOICE, status: "BUYER_REVIEW", verificationId: "VER-2026-001" }} onConfirm={() => undefined} />);

  expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Request changes" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Raise dispute" })).toBeInTheDocument();
});
