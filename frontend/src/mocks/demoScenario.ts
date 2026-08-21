import type { AgentTrace, BlockchainTransaction, RiskPassport } from "../types/agents";
import type { DocumentAnalysis, DocumentType, ExtractedField, InvoiceDocument } from "../types/documents";
import type { AgentDecision, Invoice, InvestorDashboard, RwaAsset } from "../types/invoice";
import pricing from "./generatedPricingFixture.json";

export const REQUIRED_DOCUMENT_TYPES: readonly DocumentType[] = [
  "INVOICE",
  "CONTRACT",
  "PURCHASE_ORDER",
  "DELIVERY_PROOF",
];

export const DEMO_SETTLEMENT = {
  mockKrwPerUsdc: 1_500,
  invoiceFaceValueUsdc: pricing.faceValueUsdc,
  advanceRateBps: pricing.purchaseRateBps,
  supplierAdvanceUsdc: pricing.supplierSettlementUsdc,
  investorSettlementUsdc: pricing.investorSettlementUsdc,
  platformFeeUsdc: pricing.platformFeeUsdc,
  earlySettlementCostUsdc: pricing.discountAmountUsdc,
} as const;

export const DEMO_INVOICE: Invoice = {
  id: "INV-2026-001",
  supplier: { id: "SUPPLIER_ALPHA", name: "Alpha Components", walletAddress: "8xK2...p91Q" },
  buyer: { id: "BUYER_PRIME", name: "Prime Mobility" },
  investor: { id: "INVESTOR_NOVA", name: "Nova Capital", vaultAddress: "7VB...0Qe" },
  invoiceAmount: DEMO_SETTLEMENT.invoiceFaceValueUsdc,
  currency: "USDC",
  issueDate: "2026-07-29",
  dueDate: "2026-10-30",
  deliveryDate: "2026-07-24",
  contractNumber: "PM-SUPPLY-2026-04",
  purchaseOrderNumber: "PO-89341",
  status: "DRAFT",
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
  amount: matched(DEMO_INVOICE.invoiceAmount),
  currency: matched(DEMO_INVOICE.currency),
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
  suggestedAdvanceBaseUnits: pricing.supplierSettlementBaseUnits,
  invoiceFaceValueUsdc: DEMO_SETTLEMENT.invoiceFaceValueUsdc,
  invoiceFaceValueBaseUnits: pricing.faceValueBaseUnits,
  sourceCurrencyToUsdcRate: 1,
  dataCoverageBps: 10_000,
  scoreFactors: [
    { key: "BUYER_CREDIT_QUALITY", label: "Buyer Credit Quality", score: 39, maxScore: 45, source: "SYNTHETIC_DEMO_DATA", detail: "Deterministic buyer credit profile", synthetic: true },
    { key: "BUYER_PAYMENT_HISTORY", label: "Buyer Payment History", score: 25, maxScore: 30, source: "SYNTHETIC_DEMO_DATA", detail: "Deterministic payment history", synthetic: true },
    { key: "SUPPLIER_BUYER_HISTORY", label: "Supplier–Buyer Transaction History", score: 14, maxScore: 15, source: "SYNTHETIC_DEMO_DATA", detail: "Deterministic relationship history", synthetic: true },
    { key: "REMAINING_MATURITY", label: "Remaining Maturity", score: 8, maxScore: 10, source: "INVOICE_DATA", detail: "90 days remaining", synthetic: false },
  ],
  hardGate: {
    passed: true,
    checks: [
      { key: "buyer_confirmed", label: "Buyer confirmed", passed: true },
      { key: "supplier_verified", label: "Supplier verified", passed: true },
      { key: "buyer_verified", label: "Buyer verified", passed: true },
      { key: "delivery_completed", label: "Delivery completed", passed: true },
      { key: "no_dispute", label: "No dispute", passed: true },
      { key: "no_duplicate", label: "No duplicate", passed: true },
      { key: "not_overdue", label: "Not overdue", passed: true },
      { key: "no_prior_assignment", label: "No prior assignment", passed: true },
      { key: "no_sanctions", label: "No sanctions", passed: true },
    ],
    failureReasons: [],
  },
  earlySettlementTerms: {
    faceValueUsdc: pricing.faceValueUsdc,
    faceValueBaseUnits: pricing.faceValueBaseUnits,
    discountAmountUsdc: pricing.discountAmountUsdc,
    discountRateBps: pricing.discountRateBps,
    investorRequiredReturnUsdc: pricing.investorNetReturnUsdc,
    platformFeeUsdc: pricing.platformFeeUsdc,
    platformFeeBaseUnits: pricing.platformFeeBaseUnits,
    reserveAmountUsdc: 0,
    reserveRateBps: 0,
    initialAdvanceUsdc: pricing.purchaseAmountUsdc,
    expectedReserveReturnUsdc: 0,
    expectedFinalProceedsUsdc: pricing.purchaseAmountUsdc,
    remainingTermDays: pricing.remainingTermDays,
    sofrRateBps: pricing.sofrRateBps,
    sofrAsOf: pricing.sofrAsOf,
    sofrSource: pricing.sofrSource,
    buyerRiskScore: pricing.buyerRiskScore,
    riskSpreadBps: pricing.riskSpreadBps,
    countryLegalSpreadBps: pricing.countryLegalSpreadBps,
    annualExpectedYieldBps: pricing.annualExpectedYieldBps,
    platformFeeShareBps: pricing.platformFeeShareBps,
    expectedInvestorReturnUsdc: pricing.investorNetReturnUsdc,
    investorNetReturnBaseUnits: pricing.investorNetReturnBaseUnits,
    investorSettlementUsdc: pricing.investorSettlementUsdc,
    investorSettlementBaseUnits: pricing.investorSettlementBaseUnits,
    purchaseAmountUsdc: pricing.purchaseAmountUsdc,
    purchaseAmountBaseUnits: pricing.purchaseAmountBaseUnits,
    supplierExpectedSettlementUsdc: pricing.supplierSettlementUsdc,
    supplierSettlementBaseUnits: pricing.supplierSettlementBaseUnits,
    settlementAsset: "USDC",
    network: "SOLANA_DEVNET",
  },
  modelName: "gemini-demo",
  policyVersion: "v1",
  generatedAt: "2026-07-29T09:05:00.000Z",
};

export const DEMO_FUNDING_TRANSACTION: BlockchainTransaction = {
  signature: "5igDemoFundingSignature",
  network: "SOLANA_DEVNET",
  status: "CONFIRMED",
  amountUsdc: DEMO_SETTLEMENT.supplierAdvanceUsdc,
  amountBaseUnits: pricing.supplierSettlementBaseUnits,
  fromAddress: "DEMO_AGENT_VAULT",
  toAddress: "DEMO_SUPPLIER_WALLET",
  explorerUrl: "https://explorer.solana.com/tx/5igDemoFundingSignature?cluster=devnet",
  createdAt: "2026-07-30T09:10:00.000Z",
};

export const DEMO_RWA_ASSET: RwaAsset = {
  invoiceId: DEMO_INVOICE.id,
  mintAddress: "RwaMintDemo7H4cZ8xPmN2vLq5aYtK3eW9s",
  escrowTokenAccount: "DemoRwaEscrow7H4cZ8xPmN2vLq5aYtK3eW9s",
  status: "ISSUED",
  issueTransaction: DEMO_FUNDING_TRANSACTION,
  faceValueUsdc: pricing.faceValueUsdc,
  faceValueBaseUnits: pricing.faceValueBaseUnits,
  issuancePriceUsdc: pricing.purchaseAmountUsdc,
  issuancePriceBaseUnits: pricing.purchaseAmountBaseUnits,
  purchasePriceUsdc: pricing.purchaseAmountUsdc,
  purchasePriceBaseUnits: pricing.purchaseAmountBaseUnits,
};

export const DEMO_AGENT_DECISION: AgentDecision = {
  invoiceId: DEMO_INVOICE.id,
  status: "PENDING",
  checks: { activeMandate: false },
  amountUsdc: DEMO_SETTLEMENT.supplierAdvanceUsdc,
  amountBaseUnits: pricing.purchaseAmountBaseUnits,
  reason: "활성화된 투자 Mandate를 기다리고 있습니다.",
  createdAt: "2026-07-30T09:09:00.000Z",
};

export const DEMO_SETTLEMENT_TRANSACTION: BlockchainTransaction = {
  signature: "5igDemoSettlementSignature",
  network: "SOLANA_DEVNET",
  status: "CONFIRMED",
  amountUsdc: DEMO_SETTLEMENT.invoiceFaceValueUsdc,
  amountBaseUnits: pricing.faceValueBaseUnits,
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
  investorName: DEMO_INVOICE.investor.name,
  automatedInvestmentActive: true,
  mandateStatus: "ACTIVE",
  availableVaultUsdc: 312_400,
  totalProfitUsdc: 0,
  automatedInvestmentCount: 0,
  outstandingPrincipalUsdc: 187_600,
  dueWithin30DaysUsdc: 72_840,
  attentionRequiredCount: 2,
  recentAgentTraces: DEMO_AGENT_TRACES,
};
