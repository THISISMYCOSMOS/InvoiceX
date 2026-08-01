import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import {
  DEMO_ANALYSIS,
  DEMO_DOCUMENTS,
  DEMO_FUNDING_TRANSACTION,
  DEMO_INVOICE,
  DEMO_RISK_PASSPORT,
} from "../../mocks/demoScenario";
import { SupplierInvoiceDetailContent } from "./SupplierInvoiceDetailPage";

test("shows the early settlement CTA for an offer-ready invoice", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "OFFER_READY", riskPassport: DEMO_RISK_PASSPORT }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Your early settlement offer is ready" })).toBeInTheDocument();
  expect(screen.getByText("18,800 USDC")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Decline offer" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Accept & request RWA issuance" })).toBeInTheDocument();
});

test("shows the transaction receipt for a funded invoice", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "FUNDED", fundingTransaction: DEMO_FUNDING_TRANSACTION }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Your USDC early settlement has been paid" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Transaction details" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "INV-2026-001" })).not.toBeInTheDocument();
});

test("shows the investor-purchase waiting state after RWA issuance", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "RWA_ISSUED", riskPassport: DEMO_RISK_PASSPORT }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Your RWA is ready for investor purchase" })).toBeInTheDocument();
  expect(screen.getByText("AWAITING INVESTMENT")).toBeInTheDocument();
  expect(screen.getByText("Investor purchase")).toBeInTheDocument();
});

test("shows extracted information and requests verification after confirmation", async () => {
  const user = userEvent.setup();
  const onRequestVerification = vi.fn();
  render(
    <SupplierInvoiceDetailContent
      invoice={{
        ...DEMO_INVOICE,
        status: "DOCUMENT_REVIEW_REQUIRED",
        documents: DEMO_DOCUMENTS,
        analysis: {
          ...DEMO_ANALYSIS,
          contractNumber: { ...DEMO_ANALYSIS.contractNumber, status: "REVIEW_REQUIRED" },
        },
      }}
      onAccept={() => undefined}
      onRequestVerification={onRequestVerification}
    />,
  );

  expect(screen.getByRole("heading", { name: "Review extracted information" })).toBeInTheDocument();
  expect(screen.getByText("9 of 10 verified")).toBeInTheDocument();
  expect(screen.getByText("PM-SUPPLY-2026-04")).toBeInTheDocument();
  expect(screen.getByText("Needs review")).toBeInTheDocument();
  expect(screen.getByText("Completed · July 24, 2026")).toBeInTheDocument();
  expect(screen.queryByText("03 · DOCUMENT AGENT REVIEW / 1440 × 900")).not.toBeInTheDocument();
  expect(screen.queryByText("Document Agent complete")).not.toBeInTheDocument();
  expect(screen.getByText("Prime Mobility Co., Ltd.")).toBeInTheDocument();
  expect(screen.getByText("01_Invoice_INV-2026-001.pdf")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Next document" }));
  expect(screen.getByText("02_Goods_Supply_Agreement_PM-SUPPLY-2026-04.pdf")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Previous document" }));
  expect(screen.getByText("01_Invoice_INV-2026-001.pdf")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Confirm and continue" }));
  expect(onRequestVerification).toHaveBeenCalledTimes(1);
});

test("shows the buyer-verification pending summary from the invoice", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "BUYER_REVIEW" }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Waiting for buyer verification" })).toBeInTheDocument();
  expect(screen.getByText("Prime Mobility")).toBeInTheDocument();
  expect(screen.getByText("₩20,000,000")).toBeInTheDocument();
  expect(screen.getByText("Oct 30, 2026")).toBeInTheDocument();
  expect(screen.getByText("Verification requested · Jul 29, 2026 · 10:42")).toBeInTheDocument();
  expect(screen.getByText("Buyer verification")).toHaveAttribute("aria-current", "step");
  expect(screen.queryByText("04 · BUYER VERIFICATION PENDING / 1440 × 900")).not.toBeInTheDocument();
});
