import type { AgentTrace, BlockchainTransaction, RiskPassport } from "../types/agents";
import type { DocumentAnalysis, DocumentType, ExtractedField, InvoiceDocument } from "../types/documents";
import type { Invoice, InvestorDashboard, InvestorMandate } from "../types/invoice";

export const REQUIRED_DOCUMENT_TYPES: readonly DocumentType[] = [
  "INVOICE",
  "CONTRACT",
  "PURCHASE_ORDER",
  "DELIVERY_PROOF",
];

export const DEMO_SETTLEMENT = {
  mockKrwPerUsdc: 1_000,
  invoiceFaceValueUsdc: 20_000,
  advanceRateBps: 9_400,
  supplierAdvanceUsdc: 18_800,
  investorSettlementUsdc: 19_800,
  platformFeeUsdc: 200,
  earlySettlementCostUsdc: 1_200,
} as const;

/**
 * Demo-wide constants the real screens need too: there is no FX feed and the
 * platform fee is fixed for the hackathon, so both live here rather than being
 * retyped per screen.
 */
export const KRW_PER_USDC = DEMO_SETTLEMENT.mockKrwPerUsdc;
export const PLATFORM_FEE_USDC = DEMO_SETTLEMENT.platformFeeUsdc;

/** Supplier profile fields the MVP has no signup or KYB flow to source. */
export const DEMO_SUPPLIER_PROFILE = {
  legalName: "Alpha Components Co., Ltd.",
  businessRegistrationNumber: "123-45-67890",
  representativeEnglish: "Minjun Kim",
  representativeKorean: "김민준",
  email: "finance@alphacomponents.com",
  lastConnectedAt: "2026-07-30 14:22 KST",
} as const;

export const DEMO_INVOICE: Invoice = {
  id: "INV-2026-001",
  supplier: { id: "SUPPLIER_ALPHA", name: "Alpha Components", walletAddress: "8xK2...p91Q" },
  buyer: { id: "BUYER_PRIME", name: "Prime Mobility" },
  investor: { id: "INVESTOR_NOVA", name: "Nova Capital", vaultAddress: "7VB...0Qe" },
  invoiceAmountKrw: 20_000_000,
  issueDate: "2026-07-29",
  dueDate: "2026-10-30",
  deliveryDate: "2026-07-24",
  contractNumber: "PM-SUPPLY-2026-04",
  purchaseOrderNumber: "PO-89341",
  status: "DRAFT",
  verificationRequestedAt: "2026-07-29T10:42:00+09:00",
  paymentInstructions: {
    bankName: "OOBank",
    virtualAccount: "123-456-789012",
    accountHolder: "InvoiceX Settlement Partner",
  },
  documents: [],
  agentTraces: [],
};

export const DEMO_DOCUMENTS: InvoiceDocument[] = [
  ["INVOICE", "01_Invoice_INV-2026-001.pdf"],
  ["CONTRACT", "02_Goods_Supply_Agreement_PM-SUPPLY-2026-04.pdf"],
  ["PURCHASE_ORDER", "03_Purchase_Order_PO-89341.pdf"],
  ["DELIVERY_PROOF", "04_Delivery_Acceptance_DN-2026-0724-01.pdf"],
].map(([type, fileName], index) => ({
  id: `DOC-${index + 1}`,
  invoiceId: DEMO_INVOICE.id,
  type: type as DocumentType,
  fileName,
  mimeType: "application/pdf",
  fileSize: 1024,
  uploadStatus: "COMPLETED",
}));

const matched = <T>(value: T): ExtractedField<T> => ({ value, status: "MATCHED" });

export const DEMO_ANALYSIS: DocumentAnalysis = {
  invoiceId: DEMO_INVOICE.id,
  status: "COMPLETED",
  invoiceNumber: matched(DEMO_INVOICE.id),
  supplierName: matched(DEMO_INVOICE.supplier.name),
  buyerName: matched(DEMO_INVOICE.buyer.name),
  amountKrw: matched(DEMO_INVOICE.invoiceAmountKrw),
  dueDate: matched(DEMO_INVOICE.dueDate),
  contractNumber: { value: DEMO_INVOICE.contractNumber, status: "REVIEW_REQUIRED" },
  purchaseOrderNumber: matched(DEMO_INVOICE.purchaseOrderNumber),
  deliveryCompleted: matched(true),
  modelName: "gemini-demo",
  promptVersion: "v1",
  analyzedAt: "2026-07-29T09:00:00.000Z",
};

export const DEMO_RISK_PASSPORT: RiskPassport = {
  invoiceId: DEMO_INVOICE.id,
  eligibility: "ELIGIBLE",
  riskScore: 86,
  scoreDirection: "HIGHER_IS_SAFER",
  positiveFactors: [{ title: "구매기업 검증 완료", description: "거래, 금액, 납품 완료가 확인되었습니다." }],
  riskFactors: [{ severity: "LOW", title: "단일 데모 거래", description: "해커톤 데모용 고정 시나리오입니다." }],
  suggestedAdvanceRateBps: DEMO_SETTLEMENT.advanceRateBps,
  suggestedAdvanceAmountUsdc: DEMO_SETTLEMENT.supplierAdvanceUsdc,
  modelName: "gemini-demo",
  policyVersion: "v1",
  generatedAt: "2026-07-29T09:05:00.000Z",
};

export const DEMO_FUNDING_TRANSACTION: BlockchainTransaction = {
  signature: "5igDemoFundingSignature",
  network: "SOLANA_DEVNET",
  status: "CONFIRMED",
  amountUsdc: DEMO_SETTLEMENT.supplierAdvanceUsdc,
  fromAddress: "DEMO_AGENT_VAULT",
  toAddress: "DEMO_SUPPLIER_WALLET",
  explorerUrl: "https://explorer.solana.com/tx/5igDemoFundingSignature?cluster=devnet",
  createdAt: "2026-07-30T09:10:00.000Z",
};

export const DEMO_SETTLEMENT_TRANSACTION: BlockchainTransaction = {
  signature: "5igDemoSettlementSignature",
  network: "SOLANA_DEVNET",
  status: "CONFIRMED",
  amountUsdc: DEMO_SETTLEMENT.invoiceFaceValueUsdc,
  fromAddress: "DEMO_SETTLEMENT_PARTNER",
  toAddress: "DEMO_SETTLEMENT_VAULT",
  explorerUrl: "https://explorer.solana.com/tx/5igDemoSettlementSignature?cluster=devnet",
  createdAt: "2026-10-30T09:10:00.000Z",
};

export const DEMO_AGENT_TRACES: AgentTrace[] = [
  {
    id: "TRACE-RISK-TREASURY",
    invoiceId: DEMO_INVOICE.id,
    sourceAgent: "RISK_AGENT",
    targetAgent: "TREASURY_AGENT",
    status: "COMPLETED",
    summary: "Risk Passport 전달 완료",
    createdAt: "2026-07-30T09:06:00.000Z",
    completedAt: "2026-07-30T09:06:01.000Z",
  },
];

export const DEMO_INVESTOR_DASHBOARD: InvestorDashboard = {
  vaultAddress: DEMO_INVOICE.investor.vaultAddress ?? "DEMO_AGENT_VAULT",
  investorName: DEMO_INVOICE.investor.name,
  automatedInvestmentActive: true,
  mandateStatus: "ACTIVE",
  availableVaultUsdc: 312_400,
  outstandingPrincipalUsdc: 187_600,
  dueWithin30DaysUsdc: 72_840,
  recentAgentTraces: DEMO_AGENT_TRACES,
};

export const DEMO_INVESTOR_MANDATE: InvestorMandate = {
  depositUsdc: 50_000,
  totalLimitUsdc: 50_000,
  perInvoiceLimitUsdc: 25_000,
  buyerAllowlist: ["BUYER_PRIME"],
  minimumRiskScore: 80,
  maximumTermDays: 120,
  policyExpiresOn: "2026-12-31",
  mandateId: "DEMO-MANDATE-001",
  policyHash: "demo-policy-v1",
  status: "ACTIVE",
};
