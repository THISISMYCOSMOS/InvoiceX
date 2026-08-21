import {
  DEMO_AGENT_TRACES,
  DEMO_AGENT_DECISION,
  DEMO_ANALYSIS,
  DEMO_DOCUMENTS,
  DEMO_FUNDING_TRANSACTION,
  DEMO_INVOICE,
  DEMO_INVESTOR_DASHBOARD,
  DEMO_RISK_PASSPORT,
  DEMO_RWA_ASSET,
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
    agentDecision: {
      ...clone(DEMO_AGENT_DECISION),
      status: "EXECUTED",
      checks: {
        policyActive: true,
        riskEligible: true,
        minimumRiskScore: true,
        buyerAllowlist: true,
        maximumRemainingTerm: true,
        perInvoiceLimit: true,
        totalInvestmentLimit: true,
        vaultAvailableBalance: true,
      },
      createdAt: DEMO_FUNDING_TRANSACTION.createdAt,
    },
    rwaAsset: current.rwaAsset
      ? {
        ...current.rwaAsset,
        status: "SOLD",
        purchaseTransaction: clone(DEMO_FUNDING_TRANSACTION),
        ownerVaultAddress: "DEMO_AGENT_VAULT",
      }
      : undefined,
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
    async replaceInvoiceDocuments(invoiceId) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "DOCUMENT_REVIEW_REQUIRED") {
        return invalidTransition(current, "문서 수정");
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

      const requestedAt = new Date().toISOString();
      verification = { id: "VER-2026-001", invoiceId, status: "PENDING", createdAt: requestedAt };
      invoice = {
        ...current,
        verificationId: verification.id,
        verificationRequestedAt: requestedAt,
        status: "BUYER_REVIEW",
      };
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
    async rejectVerification(verificationId, reasonCode, detail) {
      if (verification?.id !== verificationId) {
        throw new Error(`Verification ${verificationId}을(를) 찾을 수 없습니다.`);
      }
      if (invoice.status !== "BUYER_REVIEW") {
        return invalidTransition(invoice, "구매기업 거절");
      }
      verification = {
        ...verification,
        status: "REJECTED",
        rejectionReasonCode: reasonCode,
        rejectionReasonDetail: detail,
      };
      invoice = {
        ...invoice,
        status: "REJECTED",
        rejectionReasonCode: reasonCode,
        rejectionReasonDetail: detail,
      };
      return clone(invoice);
    },
    async requestRiskReview(invoiceId) {
      const current = ensureInvoice(invoiceId);
      if (current.status === "REVIEW_REQUESTED") return clone(current);
      if (current.status !== "OFFER_READY") {
        return invalidTransition(current, "Risk Score 이의 신청");
      }

      invoice = { ...current, status: "REVIEW_REQUESTED" };
      return clone(invoice);
    },
    async respondToOffer(invoiceId, response) {
      const current = ensureInvoice(invoiceId);
      if (current.status !== "OFFER_READY") {
        return invalidTransition(current, "조건 응답");
      }

      invoice = response === "ACCEPT"
        ? {
          ...current,
          status: "RWA_ISSUED",
          rwaAsset: clone(DEMO_RWA_ASSET),
          agentDecision: clone(DEMO_AGENT_DECISION),
        }
        : { ...current, status: "BLOCKED" };
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
        return invalidTransition(current, "USDC 입금 Mock");
      }

      invoice = { ...current, status: "SETTLING" };
      return clone(invoice);
    },
    async prepareBuyerPayment(invoiceId) {
      const current = ensureInvoice(invoiceId);
      const amountUsdc = current.riskPassport?.invoiceFaceValueUsdc ?? current.invoiceAmount;
      const amountBaseUnits = current.riskPassport?.invoiceFaceValueBaseUnits ?? "0";
      return {
        invoiceId,
        buyerWalletAddress: current.buyer.walletAddress ?? "11111111111111111111111111111111",
        settlementWalletAddress: "11111111111111111111111111111111",
        usdcMintAddress: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
        amountUsdc,
        amountBaseUnits,
        decimals: 6,
        dueDate: current.dueDate,
        transfers: [{
          recipientWalletAddress: "11111111111111111111111111111111",
          amountUsdc,
          amountBaseUnits,
        }],
        demoDueDateBypass: true,
        sponsored: false,
        sponsorPaymentId: null,
        sponsorWalletAddress: null,
        transactionBase64: null,
      };
    },
    async sponsorBuyerPayment(invoiceId) {
      const current = ensureInvoice(invoiceId);
      invoice = { ...current, status: "SETTLING" };
      return clone(invoice);
    },
    async confirmBuyerPayment(invoiceId) {
      const current = ensureInvoice(invoiceId);
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
          invoiceFaceValueBaseUnits: current.riskPassport?.invoiceFaceValueBaseUnits ?? "0",
          investorSettlementUsdc: DEMO_SETTLEMENT.investorSettlementUsdc,
          investorSettlementBaseUnits:
            current.riskPassport?.earlySettlementTerms?.investorSettlementBaseUnits ?? "0",
          platformFeeUsdc: DEMO_SETTLEMENT.platformFeeUsdc,
          platformFeeBaseUnits: current.riskPassport?.earlySettlementTerms?.platformFeeBaseUnits ?? "0",
          supplierResidualUsdc: 0,
          supplierResidualBaseUnits: "0",
        },
        status: "SETTLED",
      };
      return clone(invoice);
    },
    async getInvestorDashboard() {
      return clone(DEMO_INVESTOR_DASHBOARD);
    },
    async prepareInvestorDeposit() {
      throw new Error("Devnet USDC 예치는 실제 API 모드에서만 사용할 수 있습니다.");
    },
    async confirmInvestorDeposit() {
      throw new Error("Devnet USDC 예치는 실제 API 모드에서만 사용할 수 있습니다.");
    },
    async reset() {
      invoice = clone(DEMO_INVOICE);
      verification = undefined;
      return clone(invoice);
    },
  };
}
