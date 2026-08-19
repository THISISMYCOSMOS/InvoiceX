import type { InvoiceStatus } from "../types/invoice";
import { useLanguage } from "../i18n/LanguageContext";
import type { OfferStage } from "../pages/supplier/sections/EarlySettlementOfferSection";

const lifecycleStepIds = ["DOCUMENTS", "BUYER", "RISK", "TERMS", "RWA", "INVESTMENT", "SETTLEMENT"] as const;

function getCurrentLifecycleIndex(status: InvoiceStatus, offerStage: OfferStage): number {
  switch (status) {
    case "DRAFT":
    case "DOCUMENT_UPLOADING":
    case "DOCUMENT_ANALYZING":
    case "DOCUMENT_REVIEW_REQUIRED":
      return 0;
    case "BUYER_REVIEW":
      return 1;
    case "BUYER_VERIFIED":
    case "RISK_ASSESSING":
    case "REVIEW_REQUESTED":
    case "REJECTED":
      return 2;
    case "OFFER_READY":
      return offerStage === "risk" ? 2 : offerStage === "terms" ? 3 : 4;
    case "RWA_ISSUED":
    case "FUNDING":
      return 5;
    case "FUNDED":
    case "REPAYMENT_PENDING":
    case "SETTLING":
    case "SETTLEMENT_FAILED":
    case "SETTLED":
      return 6;
    case "REVISION_REQUESTED":
    case "DISPUTED":
    case "BLOCKED":
    case "ERROR":
      return 0;
  }
}

export function InvoiceProgress({ status, offerStage = "risk" }: { status: InvoiceStatus; offerStage?: OfferStage }) {
  const { t } = useLanguage();
  const currentIndex = getCurrentLifecycleIndex(status, offerStage);
  const isSettled = status === "SETTLED";
  const labels = {
    DOCUMENTS: t("Document analysis", "문서 분석"),
    BUYER: t("Buyer review", "구매기업 확인"),
    RISK: "Risk Passport",
    TERMS: t("Early-settlement terms", "조기정산 조건"),
    RWA: t("RWA issuance", "RWA 발행"),
    INVESTMENT: t("Agent investment", "Agent 자동투자"),
    SETTLEMENT: t("Maturity settlement", "만기 정산"),
  } as const;

  return (
    <div className="signup-progress invoice-lifecycle-progress" aria-label={t("Invoice lifecycle", "인보이스 진행 단계")}>
      <div>
        <strong aria-current="step">{currentIndex + 1} / {lifecycleStepIds.length} {labels[lifecycleStepIds[currentIndex]]}</strong>
        <span>{labels.SETTLEMENT}</span>
      </div>
      <i><b className="signup-progress__fill" style={{ width: `${((isSettled ? lifecycleStepIds.length : currentIndex + 1) / lifecycleStepIds.length) * 100}%` }} /></i>
    </div>
  );
}
