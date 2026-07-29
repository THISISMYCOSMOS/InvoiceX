import { render, screen } from "@testing-library/react";
import { DEMO_FUNDING_TRANSACTION, DEMO_INVOICE, DEMO_RISK_PASSPORT } from "../../mocks/demoScenario";
import { SupplierInvoiceDetailContent } from "./SupplierInvoiceDetailPage";

test("shows the early settlement CTA for an offer-ready invoice", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "OFFER_READY", riskPassport: DEMO_RISK_PASSPORT }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("button", { name: "조건 동의 및 조기정산 신청" })).toBeInTheDocument();
});

test("shows the transaction receipt for a funded invoice", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "FUNDED", fundingTransaction: DEMO_FUNDING_TRANSACTION }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByText("Transaction Hash")).toBeInTheDocument();
});
