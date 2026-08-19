import { CheckCircle, CircleNotch, ClockCountdown, WarningCircle } from "@phosphor-icons/react";
import { getInvoiceStatusLabel, type Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

type WorkflowCopy = {
  title: [string, string];
  description: [string, string];
  tone: "processing" | "attention" | "blocked";
};

function getWorkflowCopy(invoice: Invoice): WorkflowCopy {
  switch (invoice.status) {
    case "DRAFT":
    case "DOCUMENT_UPLOADING":
      return {
        title: ["Preparing your invoice documents", "인보이스 문서를 준비하고 있습니다"],
        description: ["The document set will move to analysis as soon as all required files are available.", "필수 문서가 준비되면 분석 단계로 이동합니다."],
        tone: "processing",
      };
    case "DOCUMENT_ANALYZING":
      return {
        title: ["Document Agent is extracting invoice information", "Document Agent가 인보이스 정보를 추출하고 있습니다"],
        description: ["The invoice, contract, purchase order, and delivery proof are being checked together.", "인보이스, 계약서, 발주서, 납품 증빙을 함께 확인하고 있습니다."],
        tone: "processing",
      };
    case "BUYER_VERIFIED":
    case "RISK_ASSESSING":
      return {
        title: ["Generating the Risk Passport", "Risk Passport를 생성하고 있습니다"],
        description: ["The verified invoice is being evaluated for eligibility and early-settlement terms.", "구매기업 확인을 마친 인보이스의 적격성과 조기정산 조건을 평가하고 있습니다."],
        tone: "processing",
      };
    case "REPAYMENT_PENDING":
      return {
        title: ["Waiting for maturity payment", "만기 결제를 기다리고 있습니다"],
        description: ["The buyer's USDC payment will begin the maturity-settlement process.", "구매기업의 USDC 결제가 확인되면 만기 정산을 시작합니다."],
        tone: "attention",
      };
    case "SETTLING":
      return {
        title: ["Maturity settlement is being processed", "만기 정산을 처리하고 있습니다"],
        description: ["Settlement records are being finalized for the invoice and investment position.", "인보이스와 투자 포지션의 정산 기록을 확정하고 있습니다."],
        tone: "processing",
      };
    case "REVIEW_REQUESTED":
      return {
        title: ["Review request submitted", "이의 신청이 접수되었습니다"],
        description: ["The workflow is paused with the submitted review request recorded.", "제출한 이의 신청이 기록되어 진행이 일시 중지되었습니다."],
        tone: "attention",
      };
    case "REJECTED":
      return {
        title: ["The buyer rejected this invoice", "구매기업이 인보이스를 거절했습니다"],
        description: ["Review the reason below. You can submit one review request for this MVP flow.", "아래 거절 사유를 확인하세요. MVP 흐름에서는 이의 신청을 접수할 수 있습니다."],
        tone: "blocked",
      };
    case "REVISION_REQUESTED":
      return {
        title: ["Additional information has been requested", "보완 정보가 요청되었습니다"],
        description: ["Review the buyer's request and update the invoice documents before continuing.", "구매기업 요청을 확인한 뒤 인보이스 문서를 보완해 주세요."],
        tone: "attention",
      };
    case "DISPUTED":
      return {
        title: ["The invoice is under review", "인보이스를 검토 중입니다"],
        description: ["The workflow is paused while the submitted invoice details are reviewed.", "제출된 인보이스 정보를 검토하는 동안 진행이 일시 중지됩니다."],
        tone: "blocked",
      };
    case "BLOCKED":
    case "ERROR":
      return {
        title: ["This invoice needs attention", "이 인보이스는 확인이 필요합니다"],
        description: ["The workflow could not continue. Review the invoice information and try again when it is ready.", "진행을 계속할 수 없습니다. 인보이스 정보를 확인한 뒤 준비되면 다시 시도해 주세요."],
        tone: "blocked",
      };
    default:
      return {
        title: ["Invoice workflow", "인보이스 진행 상황"],
        description: ["The latest workflow status is shown below.", "현재 진행 상태를 아래에서 확인하세요."],
        tone: "processing",
      };
  }
}

const rejectionLabels: Record<string, [string, string]> = {
  DUPLICATE_INVOICE: ["Duplicate invoice", "중복 인보이스"],
  DOCUMENT_MISMATCH: ["Invoice / contract / PO mismatch", "인보이스 / 계약서 / PO 불일치"],
  DELIVERY_INCOMPLETE: ["Delivery or service incomplete", "납품 또는 용역 미완료"],
  AMOUNT_ERROR: ["Incorrect amount", "금액 오류"],
  DUE_DATE_ERROR: ["Incorrect due date", "만기일 오류"],
  SUSPECTED_ASSIGNMENT: ["Suspected prior assignment", "기존 채권 양도 의심"],
  OTHER: ["Other", "기타"],
};

export function InvoiceWorkflowStatusSection({
  invoice,
  onRequestReview,
  isRequestingReview = false,
  reviewError,
}: {
  invoice: Invoice;
  onRequestReview?: () => void;
  isRequestingReview?: boolean;
  reviewError?: string;
}) {
  const { language, t } = useLanguage();
  const copy = getWorkflowCopy(invoice);
  const Icon = copy.tone === "blocked" ? WarningCircle : copy.tone === "attention" ? ClockCountdown : CircleNotch;
  const statusLabel = language === "ko" ? getInvoiceStatusLabel(invoice.status) : invoice.status.replaceAll("_", " ");
  const rejectionCopy = invoice.rejectionReasonCode
    ? rejectionLabels[invoice.rejectionReasonCode]
    : undefined;
  const blockedReasons = invoice.riskPassport?.hardGate?.failureReasons
    ?? invoice.riskPassport?.riskFactors.map((factor) => factor.description)
    ?? [];
  const canRequestReview = (invoice.status === "REJECTED" || invoice.status === "BLOCKED") && Boolean(onRequestReview);

  return (
    <section className={`invoice-workflow-status invoice-workflow-status--${copy.tone}`}>
      <article>
        <span className="invoice-workflow-status__icon" aria-hidden="true">
          {copy.tone === "processing" ? <Icon size={24} weight="bold" className="invoice-workflow-status__spin" /> : <Icon size={24} weight="fill" />}
        </span>
        <div>
          <span className="invoice-workflow-status__eyebrow">{statusLabel}</span>
          <h1>{t(...copy.title)}</h1>
          <p>{t(...copy.description)}</p>
        </div>
        {copy.tone === "processing" && <span className="invoice-workflow-status__live"><CheckCircle size={13} weight="fill" aria-hidden="true" /> {t("Updating", "상태 업데이트 중")}</span>}
      </article>
      {(rejectionCopy || invoice.rejectionReasonDetail || blockedReasons.length > 0) && (
        <section className="invoice-review-reasons" aria-label={t("Review reasons", "거절 및 탈락 사유")}>
          <h2>{t("Reason", "사유")}</h2>
          {rejectionCopy && <strong>{t(...rejectionCopy)}</strong>}
          {invoice.rejectionReasonDetail && <p>{invoice.rejectionReasonDetail}</p>}
          {blockedReasons.length > 0 && (
            <ul>{blockedReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
          )}
        </section>
      )}
      {canRequestReview && (
        <footer className="invoice-review-actions">
          <button type="button" className="risk-review-button" onClick={onRequestReview} disabled={isRequestingReview}>
            {isRequestingReview ? t("Submitting review request…", "이의 신청 접수 중…") : t("Request review", "이의 신청")}
          </button>
          {reviewError && <p className="offer-request-error" role="alert">{reviewError}</p>}
        </footer>
      )}
    </section>
  );
}
