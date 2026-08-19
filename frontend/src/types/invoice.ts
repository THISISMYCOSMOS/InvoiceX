import type { AgentTrace, BlockchainTransaction, RiskPassport } from "./agents";
import type { DocumentAnalysis, InvoiceDocument } from "./documents";

export type InvoiceStatus =
  | "DRAFT"
  | "DOCUMENT_UPLOADING"
  | "DOCUMENT_ANALYZING"
  | "DOCUMENT_REVIEW_REQUIRED"
  | "BUYER_REVIEW"
  | "BUYER_VERIFIED"
  | "RISK_ASSESSING"
  | "OFFER_READY"
  | "RWA_ISSUED"
  | "FUNDING"
  | "FUNDED"
  | "REPAYMENT_PENDING"
  | "SETTLING"
  | "SETTLED"
  | "REVISION_REQUESTED"
  | "DISPUTED"
  | "BLOCKED"
  | "ERROR";

export type SupplierRegistrationStep = "REGISTER" | "BUYER_REVIEW" | "VERIFIED";

const statusLabels: Record<InvoiceStatus, string> = {
  DRAFT: "등록 준비",
  DOCUMENT_UPLOADING: "문서 업로드 중",
  DOCUMENT_ANALYZING: "문서 분석 중",
  DOCUMENT_REVIEW_REQUIRED: "분석 결과 확인 필요",
  BUYER_REVIEW: "구매기업 확인 대기",
  BUYER_VERIFIED: "구매기업 검증 완료",
  RISK_ASSESSING: "Risk Passport 생성 중",
  OFFER_READY: "조기정산 조건 확인",
  RWA_ISSUED: "RWA 발행 완료",
  FUNDING: "Treasury Agent 처리 중",
  FUNDED: "USDC 지급 완료",
  REPAYMENT_PENDING: "만기 입금 대기",
  SETTLING: "온체인 정산 중",
  SETTLED: "만기 정산 완료",
  REVISION_REQUESTED: "보완 요청됨",
  DISPUTED: "이의 제기됨",
  BLOCKED: "진행 불가",
  ERROR: "처리 오류",
};

export function getInvoiceStatusLabel(status: InvoiceStatus): string {
  return statusLabels[status];
}

export function getSupplierRegistrationStep(status: InvoiceStatus): SupplierRegistrationStep {
  if (
    status === "DRAFT" ||
    status === "DOCUMENT_UPLOADING" ||
    status === "DOCUMENT_ANALYZING" ||
    status === "DOCUMENT_REVIEW_REQUIRED"
  ) {
    return "REGISTER";
  }

  return status === "BUYER_REVIEW" ? "BUYER_REVIEW" : "VERIFIED";
}

export interface InvoiceParty {
  id: string;
  name: string;
  walletAddress?: string;
  vaultAddress?: string;
}

export interface SettlementResult {
  invoiceFaceValueUsdc: number;
  investorSettlementUsdc: number;
  platformFeeUsdc: number;
  supplierResidualUsdc: number;
}

export interface RwaAsset {
  invoiceId: string;
  mintAddress: string;
  escrowTokenAccount: string;
  status: "ISSUED" | "SOLD";
  issueTransaction: BlockchainTransaction;
  faceValueUsdc?: number;
  issuancePriceUsdc?: number;
  purchaseTransaction?: BlockchainTransaction;
  ownerVaultAddress?: string;
}

export interface AgentDecision {
  invoiceId: string;
  mandateId?: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXECUTED" | "FAILED";
  checks: Record<string, boolean>;
  amountUsdc: number;
  reason?: string;
  createdAt: string;
}

export interface Invoice {
  id: string;
  supplier: InvoiceParty;
  buyer: InvoiceParty;
  investor: InvoiceParty;
  invoiceAmount: number;
  currency: string;
  issueDate: string;
  dueDate: string;
  deliveryDate: string;
  contractNumber: string;
  purchaseOrderNumber: string;
  status: InvoiceStatus;
  documents: InvoiceDocument[];
  analysis?: DocumentAnalysis;
  riskPassport?: RiskPassport;
  verificationId?: string;
  verificationRequestedAt?: string;
  verificationConfirmedAt?: string;
  fundingTransaction?: BlockchainTransaction;
  settlementTransaction?: BlockchainTransaction;
  settlement?: SettlementResult;
  rwaAsset?: RwaAsset;
  agentDecision?: AgentDecision;
  agentTraces: AgentTrace[];
}

export function formatInvoiceAmount(
  amount: number,
  currency: string,
  locale: string = "en-US",
): string {
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 6 }).format(amount)} ${currency}`;
}

export interface VerificationRequest {
  id: string;
  invoiceId: string;
  status: "PENDING" | "CONFIRMED" | "REVISION_REQUESTED" | "DISPUTED";
  createdAt?: string;
}

export interface InvestorDashboard {
  investorName: string;
  automatedInvestmentActive: boolean;
  mandateStatus: "DRAFT" | "ACTIVE";
  availableVaultUsdc: number;
  outstandingPrincipalUsdc: number;
  dueWithin30DaysUsdc: number;
  attentionRequiredCount: number;
  recentAgentTraces: AgentTrace[];
  walletAddress?: string;
  vaultAddress?: string;
  latestDeposit?: InvestorDeposit;
}

export interface InvestorDepositPreparation {
  referenceId: string;
  investorWalletAddress: string;
  treasuryWalletAddress: string;
  usdcMint: string;
  amountUsdc: number;
  decimals: number;
  network: "SOLANA_DEVNET";
}

export interface InvestorDeposit {
  referenceId: string;
  investorWalletAddress: string;
  treasuryWalletAddress: string;
  amountUsdc: number;
  signature: string;
  status: "PENDING" | "CONFIRMED" | "FAILED";
  network: "SOLANA_DEVNET";
  explorerUrl: string;
  confirmedAt: string;
}
