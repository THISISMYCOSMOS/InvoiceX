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
  modelName?: string;
  policyVersion?: string;
  generatedAt?: string;
}

export interface BlockchainTransaction {
  signature: string;
  network: "SOLANA_DEVNET";
  status: "PENDING" | "CONFIRMED" | "FAILED";
  amountUsdc: number;
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
