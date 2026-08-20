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

test("separates Risk Passport, settlement terms, and RWA issuance", async () => {
  const user = userEvent.setup();
  const onRequestRiskReview = vi.fn();
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "OFFER_READY", riskPassport: DEMO_RISK_PASSPORT }}
      onAccept={() => undefined}
      onRequestRiskReview={onRequestRiskReview}
    />,
  );

  expect(screen.getByRole("heading", { name: "Risk Passport assessment" })).toBeInTheDocument();
  expect(screen.getByText("Provisional Risk Score")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Hard Gate" })).toBeInTheDocument();
  expect(screen.getAllByText("Pass")).toHaveLength(9);
  expect(screen.queryByText("Synthetic Demo Data")).not.toBeInTheDocument();
  expect(screen.queryByText("인보이스 데이터")).not.toBeInTheDocument();
  expect(screen.getByText("3 / 7 Risk Passport")).toHaveAttribute("aria-current", "step");
  expect(screen.queryByRole("button", { name: "Decline offer" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Request Risk Score review" }));
  expect(onRequestRiskReview).toHaveBeenCalledTimes(1);

  await user.click(screen.getByRole("button", { name: "Review early-settlement terms" }));
  expect(screen.getByRole("heading", { name: "Review early-settlement terms" })).toBeInTheDocument();
  expect(screen.getByText("Annual expected yield")).toBeInTheDocument();
  expect(screen.getAllByText("RWA purchase amount").length).toBeGreaterThan(0);
  expect(screen.getByText("Dynamic Pricing")).toBeInTheDocument();
  expect(screen.getByText("4 / 7 Early-settlement terms")).toHaveAttribute("aria-current", "step");

  await user.click(screen.getByRole("button", { name: "Agree to early-settlement terms" }));
  expect(screen.getByRole("heading", { name: "Review RWA issuance" })).toBeInTheDocument();
  expect(screen.getByText("InvoiceX ID")).toBeInTheDocument();
  expect(screen.getByText("5 / 7 RWA issuance")).toHaveAttribute("aria-current", "step");
  expect(screen.getByRole("button", { name: "Request RWA issuance" })).toBeInTheDocument();
});

test("shows calculation failure instead of NaN for incomplete backend pricing", async () => {
  const user = userEvent.setup();
  const legacyTerms = {
    ...DEMO_RISK_PASSPORT.earlySettlementTerms!,
    remainingTermDays: null,
    sofrRateBps: null,
    riskSpreadBps: null,
    countryLegalSpreadBps: null,
    annualExpectedYieldBps: null,
    expectedInvestorReturnUsdc: null,
    purchaseAmountUsdc: null,
    supplierExpectedSettlementUsdc: null,
  };
  render(
    <SupplierInvoiceDetailContent
      invoice={{
        ...DEMO_INVOICE,
        status: "OFFER_READY",
        riskPassport: { ...DEMO_RISK_PASSPORT, earlySettlementTerms: legacyTerms },
      }}
      onAccept={() => undefined}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Review early-settlement terms" }));
  expect(screen.getByText("CALCULATION FAILED")).toBeInTheDocument();
  expect(screen.getByText(/Required Dynamic Pricing inputs are missing/)).toBeInTheDocument();
  expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Agree to early-settlement terms" })).toBeDisabled();
});

test("shows the review requested status and confirmation popup", async () => {
  const user = userEvent.setup();
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "REVIEW_REQUESTED", riskPassport: DEMO_RISK_PASSPORT }}
      onAccept={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Review request submitted", level: 1 })).toBeInTheDocument();
  expect(screen.getByRole("dialog")).toHaveTextContent("The invoice workflow is paused");
  await user.click(screen.getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("shows buyer rejection reason and lets the supplier request review", async () => {
  const user = userEvent.setup();
  const onRequestRiskReview = vi.fn();
  render(
    <SupplierInvoiceDetailContent
      invoice={{
        ...DEMO_INVOICE,
        status: "REJECTED",
        rejectionReasonCode: "DOCUMENT_MISMATCH",
        rejectionReasonDetail: "PO 금액과 인보이스 금액이 다릅니다.",
      }}
      onAccept={() => undefined}
      onRequestRiskReview={onRequestRiskReview}
    />,
  );

  expect(screen.getByRole("heading", { name: "The buyer rejected this invoice" })).toBeInTheDocument();
  expect(screen.getByText("Invoice / contract / PO mismatch")).toBeInTheDocument();
  expect(screen.getByText("PO 금액과 인보이스 금액이 다릅니다.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Request review" }));
  expect(onRequestRiskReview).toHaveBeenCalledTimes(1);
});

test("shows the RWA issuance request state and error instead of silently failing", async () => {
  const user = userEvent.setup();
  render(
    <SupplierInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "OFFER_READY", riskPassport: DEMO_RISK_PASSPORT }}
      onAccept={() => undefined}
      isAccepting
      acceptError="RWA 발행 요청을 처리하지 못했습니다. 다시 시도해 주세요."
    />,
  );

  await user.click(screen.getByRole("button", { name: "Review early-settlement terms" }));
  await user.click(screen.getByRole("button", { name: "Agree to early-settlement terms" }));
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

  expect(screen.getByRole("heading", { name: "Maturity settlement completed" })).toBeInTheDocument();
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

  expect(screen.getByLabelText("Invoice lifecycle")).toHaveTextContent("3 / 7 Risk Passport");
  expect(screen.getByLabelText("Invoice lifecycle")).toHaveTextContent("Maturity settlement");
  expect(screen.getByRole("heading", { name: "Generating the Risk Passport" })).toBeInTheDocument();
});

test("shows the RWA issuance summary while funding is in progress", () => {
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

  expect(screen.getByRole("heading", { name: "Your invoice RWA has been issued" })).toBeInTheDocument();
  expect(screen.getByLabelText("Invoice lifecycle")).toHaveTextContent("6 / 7 Agent investment");
  expect(screen.queryByText("Mandate evaluation")).not.toBeInTheDocument();
  expect(screen.queryByText("Expected purchase")).not.toBeInTheDocument();
  expect(screen.queryByText("Expected settlement")).not.toBeInTheDocument();
  expect(screen.queryByText("Policy checks")).not.toBeInTheDocument();
});

test("shows maturity settlement copy for a capped live Devnet payment", () => {
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

  expect(screen.getByRole("heading", { name: "Maturity settlement completed" })).toBeInTheDocument();
  expect(screen.getByText("Settlement received")).toBeInTheDocument();
  expect(screen.queryByText("A small USDC transfer verified the connected payout wallet on Solana Devnet.")).not.toBeInTheDocument();
  expect(screen.queryByText("Demo transfer only · Offer amount 2 USDC")).not.toBeInTheDocument();
  expect(screen.queryByText("DEMO VERIFIED")).not.toBeInTheDocument();
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
          invoiceNumber: { value: "DOC-INV-8842", status: "MATCHED" },
          buyerName: { value: "Document Buyer Ltd.", status: "MATCHED" },
          amount: { value: 4920.5, status: "MATCHED" },
          currency: { value: "EUR", status: "MATCHED" },
          dueDate: { value: "2026-12-18", status: "MATCHED" },
          contractNumber: { ...DEMO_ANALYSIS.contractNumber, status: "REVIEW_REQUIRED" },
          purchaseOrderNumber: { value: "PO-DOC-019", status: "MATCHED" },
        },
      }}
      onAccept={() => undefined}
      onRequestVerification={onRequestVerification}
    />,
  );

  expect(screen.getByRole("heading", { name: "Review extracted information" })).toBeInTheDocument();
  expect(screen.getByText("2 / 3 Review extraction")).toBeInTheDocument();
  expect(screen.getByText("7 of 8 verified")).toBeInTheDocument();
  expect(screen.getByText("DOC-INV-8842")).toBeInTheDocument();
  expect(screen.getByText("Document Buyer Ltd.")).toBeInTheDocument();
  expect(screen.getByText("4,920.5 EUR")).toBeInTheDocument();
  expect(screen.getByText("December 18, 2026")).toBeInTheDocument();
  expect(screen.getByText("PM-SUPPLY-2026-04")).toBeInTheDocument();
  expect(screen.getByText("PO-DOC-019")).toBeInTheDocument();
  expect(screen.getByText(/contract number differs between documents or could not be confirmed/i)).toBeInTheDocument();
  expect(screen.getByText("Needs review")).toBeInTheDocument();
  expect(screen.getByText("Completed")).toBeInTheDocument();
  expect(screen.queryByText("03 · DOCUMENT AGENT REVIEW / 1440 × 900")).not.toBeInTheDocument();
  expect(screen.queryByText("Document Agent complete")).not.toBeInTheDocument();
  expect(screen.getByText("01_Invoice_INV-2026-001.pdf")).toBeInTheDocument();

  await user.click(screen.getByRole("tab", { name: "Contract" }));
  expect(screen.getByText("02_Goods_Supply_Agreement_PM-SUPPLY-2026-04.pdf")).toBeInTheDocument();

  await user.click(screen.getByRole("tab", { name: "Invoice" }));
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
  expect(screen.getByText("3 / 3 Buyer review requested")).toHaveAttribute("aria-current", "step");
  expect(screen.queryByRole("list", { name: "Buyer verification progress" })).not.toBeInTheDocument();
  expect(screen.queryByText("04 · BUYER VERIFICATION PENDING / 1440 × 900")).not.toBeInTheDocument();
});
