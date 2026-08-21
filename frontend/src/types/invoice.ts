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
  | "REJECTED"
  | "REVIEW_REQUESTED"
  | "RWA_ISSUED"
  | "FUNDING"
  | "FUNDED"
  | "REPAYMENT_PENDING"
  | "SETTLING"
  | "SETTLED"
  | "SETTLEMENT_FAILED"
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
  REJECTED: "구매기업 거절",
  REVIEW_REQUESTED: "Review Requested",
  RWA_ISSUED: "RWA 발행 완료",
  FUNDING: "Treasury Agent 처리 중",
  FUNDED: "USDC 지급 완료",
  REPAYMENT_PENDING: "만기 입금 대기",
  SETTLING: "온체인 정산 중",
  SETTLED: "만기 정산 완료",
  SETTLEMENT_FAILED: "정산 재시도 필요",
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
  invoiceFaceValueBaseUnits: string;
  investorSettlementUsdc: number;
  investorSettlementBaseUnits: string;
  platformFeeUsdc: number;
  platformFeeBaseUnits: string;
  supplierResidualUsdc: number;
  supplierResidualBaseUnits: string;
}

export interface RwaAsset {
  invoiceId: string;
  mintAddress: string;
  escrowTokenAccount: string;
  status: "ISSUED" | "SOLD" | "SETTLED";
  issueTransaction: BlockchainTransaction;
  faceValueUsdc?: number;
  faceValueBaseUnits?: string;
  issuancePriceUsdc?: number;
  issuancePriceBaseUnits?: string;
  purchasePriceUsdc?: number;
  purchasePriceBaseUnits?: string;
  purchaseTransaction?: BlockchainTransaction;
  ownerVaultAddress?: string;
}

export interface AgentDecision {
  invoiceId: string;
  mandateId?: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXECUTED" | "FAILED";
  checks: Record<string, boolean>;
  amountUsdc: number;
  amountBaseUnits: string;
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
  verificationRejectedAt?: string;
  rejectionReasonCode?: string;
  rejectionReasonDetail?: string;
  reviewRequestedAt?: string;
  fundingTransaction?: BlockchainTransaction;
  settlementTransaction?: BlockchainTransaction;
  buyerPaymentTransaction?: BlockchainTransaction;
  investorPayoutTransaction?: BlockchainTransaction;
  platformFeeTransaction?: BlockchainTransaction;
  buyerPaidAt?: string;
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
  status: "PENDING" | "CONFIRMED" | "REJECTED" | "REVISION_REQUESTED" | "DISPUTED";
  createdAt?: string;
  rejectionReasonCode?: string;
  rejectionReasonDetail?: string;
  respondedAt?: string;
}

export type BuyerRejectionReason =
  | "DUPLICATE_INVOICE"
  | "DOCUMENT_MISMATCH"
  | "DELIVERY_INCOMPLETE"
  | "AMOUNT_ERROR"
  | "DUE_DATE_ERROR"
  | "SUSPECTED_ASSIGNMENT"
  | "OTHER";

export interface BuyerPaymentPreparation {
  invoiceId: string;
  buyerWalletAddress: string;
  settlementWalletAddress: string;
  usdcMintAddress: string;
  amountUsdc: number;
  amountBaseUnits: string;
  decimals: number;
  dueDate: string;
  transfers: Array<{
    recipientWalletAddress: string;
    amountUsdc: number;
    amountBaseUnits: string;
  }>;
  demoDueDateBypass: boolean;
  sponsored: boolean;
  sponsorPaymentId: string | null;
  sponsorWalletAddress: string | null;
  transactionBase64: string | null;
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
  amountBaseUnits: string;
  decimals: number;
  network: "SOLANA_DEVNET";
}

export interface InvestorDeposit {
  referenceId: string;
  investorWalletAddress: string;
  treasuryWalletAddress: string;
  amountUsdc: number;
  amountBaseUnits: string;
  signature: string;
  status: "PENDING" | "CONFIRMED" | "FAILED";
  network: "SOLANA_DEVNET";
  explorerUrl: string;
  confirmedAt: string;
}
