export interface RiskPassport {
  invoiceId: string;
  eligibility: "ELIGIBLE" | "REVIEW_REQUIRED" | "BLOCKED";
  riskScore: number | null;
  scoreDirection: "HIGHER_IS_SAFER";
  positiveFactors: Array<{ title: string; description: string }>;
  riskFactors: Array<{
    severity: "LOW" | "MEDIUM" | "HIGH";
    title: string;
    description: string;
  }>;
  suggestedAdvanceRateBps: number | null;
  suggestedAdvanceAmountUsdc: number | null;
  suggestedAdvanceBaseUnits?: string | null;
  invoiceFaceValueUsdc?: number | null;
  invoiceFaceValueBaseUnits?: string | null;
  sourceCurrencyToUsdcRate?: number | null;
  dataCoverageBps: number;
  scoreFactors: Array<{
    key: string;
    label: string;
    score: number | null;
    maxScore: number;
    source: "SYNTHETIC_DEMO_DATA" | "INVOICE_DATA" | "INVOICEX_DATA" | "DOCUMENT_AGENT";
    detail?: string;
    synthetic: boolean;
  }>;
  hardGate?: {
    passed: boolean;
    checks: Array<{ key: string; label: string; passed: boolean; reason?: string }>;
    failureReasons: string[];
  } | null;
  earlySettlementTerms?: {
    faceValueUsdc: number;
    faceValueBaseUnits: string;
    discountAmountUsdc: number;
    discountRateBps: number;
    investorRequiredReturnUsdc: number;
    platformFeeUsdc: number;
    platformFeeBaseUnits: string;
    reserveAmountUsdc: number;
    reserveRateBps: number;
    initialAdvanceUsdc: number;
    expectedReserveReturnUsdc: number;
    expectedFinalProceedsUsdc: number;
    remainingTermDays: number | null;
    sofrRateBps: number | null;
    sofrAsOf: string | null;
    sofrSource: string | null;
    buyerRiskScore: number | null;
    riskSpreadBps: number | null;
    countryLegalSpreadBps: number | null;
    annualExpectedYieldBps: number | null;
    platformFeeShareBps: number | null;
    expectedInvestorReturnUsdc: number | null;
    investorNetReturnBaseUnits: string | null;
    investorSettlementUsdc: number | null;
    investorSettlementBaseUnits: string | null;
    purchaseAmountUsdc: number | null;
    purchaseAmountBaseUnits: string | null;
    supplierExpectedSettlementUsdc: number | null;
    supplierSettlementBaseUnits: string | null;
    settlementAsset: "USDC";
    network: "SOLANA_DEVNET";
  } | null;
  modelName?: string;
  policyVersion?: string;
  generatedAt?: string;
}

export interface BlockchainTransaction {
  signature: string;
  network: "SOLANA_DEVNET";
  status: "PENDING" | "CONFIRMED" | "FAILED";
  amountUsdc: number;
  amountBaseUnits: string;
  fromAddress: string;
  toAddress: string;
  explorerUrl: string;
  createdAt: string;
}

export interface AgentTrace {
  id: string;
  invoiceId: string;
  sourceAgent: "DOCUMENT_AGENT" | "RISK_AGENT" | "TREASURY_AGENT" | "SETTLEMENT_AGENT";
  targetAgent: "RISK_AGENT" | "TREASURY_AGENT" | "SETTLEMENT_AGENT";
  status: "SUBMITTED" | "WORKING" | "COMPLETED" | "FAILED";
  summary: string;
  createdAt: string;
  completedAt?: string;
}

export interface AgentActivityItem {
  id: string;
  kind: "RUN" | "TOOL" | "HANDOFF";
  status: string;
  title: string;
  summary: string;
  createdAt: string;
  methodVersion?: string;
  checks?: Record<string, boolean>;
  transactionSignature?: string;
  explorerUrl?: string;
}

export interface AgentActivityTimeline {
  invoiceId: string;
  role: "Supplier" | "Investor";
  runs: Array<{ id: string; status: string; trigger: string; planSummary: string; createdAt: string }>;
  timeline: AgentActivityItem[];
}
