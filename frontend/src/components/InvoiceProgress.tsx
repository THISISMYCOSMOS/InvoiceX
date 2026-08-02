import type { InvoiceStatus } from "../types/invoice";
import { useLanguage } from "../i18n/LanguageContext";

const lifecycleStepIds = ["DOCUMENTS", "BUYER", "RISK", "RWA", "INVESTMENT", "SETTLEMENT"] as const;

function getCurrentLifecycleIndex(status: InvoiceStatus): number {
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
      return 2;
    case "OFFER_READY":
      return 3;
    case "RWA_ISSUED":
    case "FUNDING":
      return 4;
    case "FUNDED":
    case "REPAYMENT_PENDING":
    case "SETTLING":
    case "SETTLED":
      return 5;
    case "REVISION_REQUESTED":
    case "DISPUTED":
    case "BLOCKED":
    case "ERROR":
      return 0;
  }
}

export function InvoiceProgress({ status }: { status: InvoiceStatus }) {
  const { t } = useLanguage();
  const currentIndex = getCurrentLifecycleIndex(status);
  const isSettled = status === "SETTLED";
  const labels = {
    DOCUMENTS: t("Document analysis", "문서 분석"),
    BUYER: t("Buyer review", "구매기업 확인"),
    RISK: "Risk Passport",
    RWA: t("RWA issuance", "RWA 발행"),
    INVESTMENT: t("Agent investment", "Agent 자동 투자"),
    SETTLEMENT: t("Maturity settlement", "만기 정산"),
  } as const;

  return (
    <ol className="invoice-progress invoice-progress--lifecycle" aria-label={t("Invoice lifecycle", "인보이스 진행 단계")}>
      {lifecycleStepIds.map((step, index) => {
        const isComplete = isSettled || index < currentIndex;
        const isCurrent = !isSettled && index === currentIndex;
        return (
          <li key={step} className={isComplete ? "is-complete" : isCurrent ? "is-current" : ""} aria-current={isCurrent ? "step" : undefined}>
            <span className="invoice-progress__number">{isComplete ? "✓" : index + 1}</span>
            <span>{labels[step]}</span>
          </li>
        );
      })}
    </ol>
  );
}
