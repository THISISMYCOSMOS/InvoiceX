import {
  DEMO_AGENT_TRACES,
  DEMO_ANALYSIS,
  DEMO_DOCUMENTS,
  DEMO_FUNDING_TRANSACTION,
  DEMO_INVOICE,
  DEMO_INVESTOR_DASHBOARD,
  DEMO_RISK_PASSPORT,
  DEMO_SETTLEMENT,
  DEMO_SETTLEMENT_TRANSACTION,
} from "../../mocks/demoScenario";
import type { Invoice, VerificationRequest } from "../../types/invoice";
import type { ScenarioAdapter } from "./contracts";

function clone<T>(value: T): T {
  return structuredClone(value);
}

function invalidTransition(invoice: Invoice, action: string): never {
  throw new Error(`${invoice.id}은(는) ${invoice.status} 상태에서 ${action}을(를) 실행할 수 없습니다.`);
}

export function createMockAdapter(): ScenarioAdapter {
  let invoice = clone(DEMO_INVOICE);
  let verification: VerificationRequest | undefined;

  const completeFunding = (current: Invoice): Invoice => ({
    ...current,
    agentTraces: clone(DEMO_AGENT_TRACES),
    fundingTransaction: clone(DEMO_FUNDING_TRANSACTION),
    status: "FUNDED",
  });

  const ensureInvoice = (invoiceId: string): Invoice => {
    if (invoiceId !== invoice.id) {
      throw new Error(`Invoice ${invoiceId}을(를) 찾을 수 없습니다.`);
    }

    return invoice;
  };

  return {
    async submitInvoiceDocuments() {
      const current = ensureInvoice(invoice.id);
      if (current.status !== "DRAFT" && current.status !== "DOCUMENT_UPLOADING") {
        return invalidTransition(current, "문서 등록");
      }

      invoice = {
        ...current,
        documents: clone(DEMO_DOCUMENTS),
        analysis: clone(DEMO_ANALYSIS),
        status: "DOCUMENT_REVIEW_REQUIRED",
      };
      return clone(invoice);
    },
    async getInvoices() {
      return [clone(invoice)];
    },
    async getInvoice(invoiceId) {
      return clone(ensureInvoice(invoiceId));
    },
    async analyzeInvoice(invoiceId) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "DRAFT" && current.status !== "DOCUMENT_UPLOADING") {
        return invalidTransition(current, "문서 분석");
      }

      invoice = {
        ...current,
        documents: clone(DEMO_DOCUMENTS),
        analysis: clone(DEMO_ANALYSIS),
        status: "DOCUMENT_REVIEW_REQUIRED",
      };
      return clone(invoice);
    },
    async requestVerification(invoiceId) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "DOCUMENT_REVIEW_REQUIRED") {
        return invalidTransition(current, "검증 요청");
      }

      verification = { id: "VER-2026-001", invoiceId, status: "PENDING" };
      invoice = { ...current, verificationId: verification.id, status: "BUYER_REVIEW" };
      return clone(invoice);
    },
    async getVerifications() {
      return verification ? [clone(verification)] : [];
    },
    async getVerification(verificationId) {
      if (verification?.id !== verificationId) {
        throw new Error(`Verification ${verificationId}을(를) 찾을 수 없습니다.`);
      }

      return clone(verification);
    },
    async confirmVerification(verificationId) {
      if (verification?.id !== verificationId) {
        throw new Error(`Verification ${verificationId}을(를) 찾을 수 없습니다.`);
      }
      if (invoice.status !== "BUYER_REVIEW") {
        return invalidTransition(invoice, "구매기업 확인");
      }

      verification = { ...verification, status: "CONFIRMED" };
      invoice = { ...invoice, riskPassport: clone(DEMO_RISK_PASSPORT), status: "OFFER_READY" };
      return clone(invoice);
    },
    async respondToOffer(invoiceId, response) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "OFFER_READY") {
        return invalidTransition(current, "조건 응답");
      }

      invoice = { ...current, status: response === "ACCEPT" ? "RWA_ISSUED" : "BLOCKED" };
      return clone(invoice);
    },
    async purchaseRwa(invoiceId) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "RWA_ISSUED") {
        return invalidTransition(current, "투자기관 RWA 매수");
      }

      invoice = completeFunding(current);
      return clone(invoice);
    },
    async runFunding(invoiceId) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "RWA_ISSUED" && current.status !== "FUNDING") {
        return invalidTransition(current, "Treasury Agent 투자");
      }

      invoice = completeFunding(current);
      return clone(invoice);
    },
    async mockPayment(invoiceId) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "FUNDED") {
        return invalidTransition(current, "원화 입금 Mock");
      }

      invoice = { ...current, status: "SETTLING" };
      return clone(invoice);
    },
    async runSettlement(invoiceId) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "SETTLING") {
        return invalidTransition(current, "Settlement");
      }

      invoice = {
        ...current,
        settlementTransaction: clone(DEMO_SETTLEMENT_TRANSACTION),
        settlement: {
          invoiceFaceValueUsdc: DEMO_SETTLEMENT.invoiceFaceValueUsdc,
          investorSettlementUsdc: DEMO_SETTLEMENT.investorSettlementUsdc,
          platformFeeUsdc: DEMO_SETTLEMENT.platformFeeUsdc,
          supplierResidualUsdc: 0,
        },
        status: "SETTLED",
      };
      return clone(invoice);
    },
    async getInvestorDashboard() {
      return clone(DEMO_INVESTOR_DASHBOARD);
    },
    async reset() {
      invoice = clone(DEMO_INVOICE);
      verification = undefined;
      return clone(invoice);
    },
  };
}
