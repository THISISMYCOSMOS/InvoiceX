import { getInvoiceStatusLabel, type InvoiceStatus } from "../types/invoice";
import { useLanguage } from "../i18n/LanguageContext";

const englishStatusLabels: Record<InvoiceStatus, string> = {
  DRAFT: "Draft",
  DOCUMENT_UPLOADING: "Uploading documents",
  DOCUMENT_ANALYZING: "Analyzing documents",
  DOCUMENT_REVIEW_REQUIRED: "Review required",
  BUYER_REVIEW: "Buyer review",
  BUYER_VERIFIED: "Buyer verified",
  RISK_ASSESSING: "Generating Risk Passport",
  OFFER_READY: "Offer ready",
  RWA_ISSUED: "RWA issued",
  FUNDING: "Treasury Agent processing",
  FUNDED: "USDC funded",
  REPAYMENT_PENDING: "Repayment pending",
  SETTLING: "On-chain settlement",
  SETTLED: "Settled",
  REVISION_REQUESTED: "Revision requested",
  DISPUTED: "Disputed",
  BLOCKED: "Blocked",
  ERROR: "Processing error",
};

export function StatusBadge({ status }: { status: InvoiceStatus }) {
  const { language, t } = useLanguage();
  const label = language === "ko" ? getInvoiceStatusLabel(status) : englishStatusLabels[status];
  return <span className="ml-2 inline-flex rounded-full bg-invoicex-50 px-2.5 py-1 text-xs font-semibold text-invoicex-700" aria-label={`${t("Status", "상태")}: ${label}`}>{label}</span>;
}
