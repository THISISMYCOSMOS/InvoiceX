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

  expect(screen.getByRole("heading", { name: "Your RWA issuance preparation is complete" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "2 USDC" })).toBeInTheDocument();
  expect(screen.getByText("0.13 USDC")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Risk Passport" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Decline offer" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Request RWA issuance" })).toBeInTheDocument();
});

test("shows the RWA issuance request state and error instead of silently failing", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "OFFER_READY", riskPassport: DEMO_RISK_PASSPORT }}
      onAccept={() => undefined}
      isAccepting
      acceptError="RWA 발행 요청을 처리하지 못했습니다. 다시 시도해 주세요."
    />,
  );

  expect(screen.getByRole("button", { name: "Requesting RWA issuance…" })).toBeDisabled();
  expect(screen.getByRole("alert")).toHaveTextContent("RWA 발행 요청을 처리하지 못했습니다.");
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

test("shows the supplier RWA issuance summary after RWA issuance", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "RWA_ISSUED", riskPassport: DEMO_RISK_PASSPORT }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Your invoice RWA has been issued" })).toBeInTheDocument();
  expect(screen.getByText("RWA ISSUED")).toBeInTheDocument();
  expect(screen.getByText("Invoice ID")).toBeInTheDocument();
  expect(screen.getByText("Supplier")).toBeInTheDocument();
  expect(screen.getByText("Buyer")).toBeInTheDocument();
  expect(screen.getByText("Risk Passport score")).toBeInTheDocument();
  expect(screen.getByText("RWA asset details")).toBeInTheDocument();
  expect(screen.getByText("Delivery date")).toBeInTheDocument();
  expect(screen.queryByText("Treasury Agent is processing the RWA investment")).not.toBeInTheDocument();
});

test("shows the shared lifecycle for an in-progress risk assessment", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "RISK_ASSESSING" }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("list", { name: "Invoice lifecycle" })).toHaveTextContent("Document analysis");
  expect(screen.getByRole("list", { name: "Invoice lifecycle" })).toHaveTextContent("Maturity settlement");
  expect(screen.getByRole("heading", { name: "Generating the Risk Passport" })).toBeInTheDocument();
});

test("shows Agent policy evaluation details while funding is in progress", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{
        ...DEMO_INVOICE,
        status: "FUNDING",
        riskPassport: DEMO_RISK_PASSPORT,
        agentDecision: {
          invoiceId: DEMO_INVOICE.id,
          status: "APPROVED",
          checks: { minimumRiskScore: true, buyerAllowlist: true },
          amountUsdc: 1,
          reason: "All signed investment criteria passed.",
          createdAt: "2026-07-30T09:06:00.000Z",
        },
      }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Treasury Agent is evaluating this issued RWA" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Policy checks" })).toBeInTheDocument();
  expect(screen.getByText("minimumRiskScore")).toBeInTheDocument();
  expect(screen.getAllByText("Passed")).toHaveLength(2);
});

test("labels a capped live Devnet payment as a demo transfer", () => {
  render(
    <SupplierInvoiceDetailContent
      invoice={{
        ...DEMO_INVOICE,
        status: "FUNDED",
        riskPassport: {
          ...DEMO_RISK_PASSPORT,
          suggestedAdvanceAmountUsdc: 2,
        },
        fundingTransaction: {
          ...DEMO_FUNDING_TRANSACTION,
          amountUsdc: 1,
        },
      }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Devnet demo transfer confirmed" })).toBeInTheDocument();
  expect(screen.getByText("Demo transfer only · Offer amount 2 USDC")).toBeInTheDocument();
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
  expect(screen.getByText("3 USDC")).toBeInTheDocument();
  expect(screen.getByText("Oct 30, 2026")).toBeInTheDocument();
  expect(screen.getByText("Verification requested · Jul 29, 2026 · 10:42")).toBeInTheDocument();
  expect(screen.getByText("Buyer verification")).toHaveAttribute("aria-current", "step");
  expect(screen.queryByText("04 · BUYER VERIFICATION PENDING / 1440 × 900")).not.toBeInTheDocument();
});
