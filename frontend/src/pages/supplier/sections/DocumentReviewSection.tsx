import {
  ArrowRight,
  CheckCircle,
  Warning,
} from "@phosphor-icons/react";
import { useState } from "react";
import invoicePreview from "../../../assets/invoice-preview.png";
import { InvoiceRegistrationProgress } from "../../../components/InvoiceRegistrationProgress";
import { useLanguage } from "../../../i18n/LanguageContext";
import type { DocumentType, ExtractedField } from "../../../types/documents";
import type { Invoice } from "../../../types/invoice";

interface DocumentReviewSectionProps {
  invoice: Invoice;
  onConfirm: () => void;
  isPending?: boolean;
}

const documentTabs: Array<{ type: DocumentType; english: string; korean: string }> = [
  { type: "INVOICE", english: "Invoice", korean: "인보이스" },
  { type: "CONTRACT", english: "Contract", korean: "계약서" },
  { type: "PURCHASE_ORDER", english: "PO", korean: "발주서" },
  { type: "DELIVERY_PROOF", english: "Delivery proof", korean: "납품 증빙" },
];
function ReviewField({
  label,
  field,
  value,
  note,
}: {
  label: string;
  field: ExtractedField<unknown>;
  value: string;
  note?: string;
}) {
  const { t } = useLanguage();
  const needsReview = field.status !== "MATCHED";
  return (
    <section className={`review-field ${needsReview ? "needs-review" : ""}`}>
      <div className="review-field__meta">
        <span>{label}</span>
        <span className={needsReview ? "review-field__warning" : "review-field__verified"}>
          {needsReview ? (
            <>
              <Warning aria-hidden="true" size={11} weight="fill" />
              {t("Needs review", "확인 필요")}
            </>
          ) : (
            <>
              <CheckCircle aria-hidden="true" size={11} weight="fill" />
              {t("Found in document", "문서에서 확인")}
            </>
          )}
        </span>
      </div>
      <strong>{value}</strong>
      {note && <p>{note}</p>}
    </section>
  );
}

export function DocumentReviewSection({ invoice, onConfirm, isPending = false }: DocumentReviewSectionProps) {
  const { language, t } = useLanguage();
  const [activeDocumentIndex, setActiveDocumentIndex] = useState(0);
  const analysis = invoice.analysis;
  if (!analysis) {
    return (
      <section className="review-missing" role="alert">
        <h2>{t("Analysis data is unavailable", "분석 데이터를 불러올 수 없습니다")}</h2>
        <p>{t("Refresh the invoice after Document Agent finishes processing.", "Document Agent 처리가 끝난 뒤 인보이스를 새로고침하세요.")}</p>
      </section>
    );
  }

  const reviewDocuments = invoice.documents.filter((document) => (
    document.type === "INVOICE"
    || document.type === "CONTRACT"
    || document.type === "PURCHASE_ORDER"
    || document.type === "DELIVERY_PROOF"
  ));
  const activeDocument = reviewDocuments[activeDocumentIndex] ?? reviewDocuments[0];
  const documentCount = reviewDocuments.length;
  const activeDocumentNumber = activeDocument ? Math.min(activeDocumentIndex, documentCount - 1) + 1 : 0;
  const documentTypeLabel = (type: DocumentType) => {
    const labels: Record<DocumentType, [string, string]> = {
      INVOICE: ["Invoice", "인보이스"],
      CONTRACT: ["Contract", "계약서"],
      PURCHASE_ORDER: ["Purchase order", "발주서"],
      DELIVERY_PROOF: ["Delivery proof", "납품 증빙"],
    };
    return t(...labels[type]);
  };
  const selectDocument = (type: DocumentType) => {
    const documentIndex = reviewDocuments.findIndex((document) => document.type === type);
    if (documentIndex >= 0) setActiveDocumentIndex(documentIndex);
  };
  const longDateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  const notFound = t("Not found", "찾을 수 없음");
  const formatExtractedDate = (value: string | null) => {
    if (!value) return notFound;
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? value : longDateFormatter.format(date);
  };
  const currency = analysis.currency.value;
  const amountField: ExtractedField<unknown> = (
    analysis.amount.status === "MATCHED" && analysis.currency.status === "MATCHED"
  ) ? analysis.amount : { ...analysis.amount, status: "REVIEW_REQUIRED" };
  const displayedFields = [
    analysis.invoiceNumber,
    analysis.buyerName,
    analysis.amount,
    analysis.currency,
    analysis.dueDate,
    analysis.contractNumber,
    analysis.purchaseOrderNumber,
    analysis.deliveryCompleted,
  ];
  const reviewRequiredCount = displayedFields.filter((field) => field.status !== "MATCHED").length;
  const verifiedCount = displayedFields.length - reviewRequiredCount;

  return (
    <section className="document-review-page">
      <header className="review-heading">
        <div>
          <p className="breadcrumb">{t("Invoices / New invoice / Review extraction", "인보이스 / 새 인보이스 / 추출 정보 확인")}</p>
          <h1>{t("Review extracted information", "추출 정보 확인")}</h1>
          <p>{t("Compare the original document with the values found by Document Agent.", "원본 문서와 Document Agent가 찾은 값을 비교하세요.")}</p>
        </div>
        <span className="verification-count">
          {t(`${verifiedCount} of ${displayedFields.length} verified`, `${displayedFields.length}개 중 ${verifiedCount}개 검증`)}
        </span>
      </header>

      <InvoiceRegistrationProgress step={2} />

      <div className="review-layout">
        <section className="document-review-preview" aria-label={t("Uploaded document preview", "업로드 문서 미리보기")}>
          <header className="document-review-preview__header">
            <div>
              <span className="document-review-preview__type">
                {activeDocument ? documentTypeLabel(activeDocument.type) : t("Uploaded document", "업로드 문서")}
              </span>
              <strong>{activeDocument?.fileName ?? t("No document available", "표시할 문서가 없습니다")}</strong>
            </div>
            <span className="document-review-preview__count">
              {t(`${activeDocumentNumber} of ${documentCount} documents`, `총 ${documentCount}개 중 ${activeDocumentNumber}개`)}
            </span>
          </header>
          <div className="document-tabs document-review-tabs" role="tablist" aria-label={t("Uploaded document types", "업로드 문서 유형")}>
            {documentTabs.map((tab) => {
              const isAvailable = reviewDocuments.some((document) => document.type === tab.type);
              return (
                <button
                  key={tab.type}
                  type="button"
                  role="tab"
                  aria-selected={activeDocument?.type === tab.type}
                  className={activeDocument?.type === tab.type ? "is-active" : ""}
                  onClick={() => selectDocument(tab.type)}
                  disabled={!isAvailable}
                >
                  {t(tab.english, tab.korean)}
                </button>
              );
            })}
          </div>
          <div className="document-review-preview__body">
            <div className="document-review-preview__frame">
              {activeDocument?.storageUrl ? (
                <iframe title={activeDocument.fileName} src={activeDocument.storageUrl} />
              ) : (
                <img
                  src={invoicePreview}
                  alt={t(`${activeDocument ? documentTypeLabel(activeDocument.type) : ""} document preview`, `${activeDocument ? documentTypeLabel(activeDocument.type) : ""} 문서 미리보기`)}
                />
              )}
            </div>
          </div>
        </section>

        <div className="review-fields">
          <ReviewField label={t("INVOICE ID", "인보이스 ID")} field={analysis.invoiceNumber} value={analysis.invoiceNumber.value ?? notFound} />
          <ReviewField label={t("BUYER", "구매자")} field={analysis.buyerName} value={analysis.buyerName.value ?? notFound} />
          <ReviewField
            label={t("INVOICE AMOUNT", "인보이스 금액")}
            field={amountField}
            value={analysis.amount.value === null
              ? notFound
              : `${new Intl.NumberFormat(language === "ko" ? "ko-KR" : "en-US").format(analysis.amount.value)}${currency ? ` ${currency}` : ""}`}
          />
          <ReviewField label={t("DUE DATE", "만기일")} field={analysis.dueDate} value={formatExtractedDate(analysis.dueDate.value)} />
          <ReviewField
            label={t("CONTRACT NUMBER", "계약번호")}
            field={analysis.contractNumber}
            value={analysis.contractNumber.value ?? notFound}
            note={analysis.contractNumber.status === "MATCHED" ? undefined : t(
              "The contract number differs between documents or could not be confirmed. Compare the invoice and contract before continuing.",
              "계약번호가 문서 간 다르거나 명확히 확인되지 않았습니다. 인보이스와 계약서 원문을 비교해 확인하세요.",
            )}
          />
          <ReviewField
            label={t("PO NUMBER", "발주번호")}
            field={analysis.purchaseOrderNumber}
            value={analysis.purchaseOrderNumber.value ?? notFound}
            note={analysis.purchaseOrderNumber.status === "MATCHED" ? undefined : t(
              "The purchase-order number differs between documents or could not be confirmed. Compare the invoice, PO and delivery proof.",
              "발주번호가 문서 간 다르거나 명확히 확인되지 않았습니다. 인보이스·발주서·납품증빙 원문을 비교해 확인하세요.",
            )}
          />
          <ReviewField
            label={t("DELIVERY STATUS", "납품 상태")}
            field={analysis.deliveryCompleted}
            value={analysis.deliveryCompleted.value === null
              ? notFound
              : analysis.deliveryCompleted.value ? t("Completed", "완료") : t("Not completed", "미완료")}
          />
        </div>
      </div>

      <footer className="review-actions">
        <p>{reviewRequiredCount > 0
          ? t(
            `${reviewRequiredCount} extracted field(s) need confirmation before sending to the buyer.`,
            `구매자에게 보내기 전에 추출 항목 ${reviewRequiredCount}개를 확인해야 합니다.`,
          )
          : t("All extracted fields were verified against the uploaded documents.", "모든 추출 항목이 업로드 문서에서 확인되었습니다.")}</p>
        <button className="primary-button review-confirm" type="button" onClick={onConfirm} disabled={isPending}>
          {isPending ? t("Requesting verification...", "검증 요청 중...") : t("Confirm and continue", "확인 후 계속")}
          {!isPending && <ArrowRight aria-hidden="true" size={14} weight="bold" />}
        </button>
      </footer>
    </section>
  );
}
