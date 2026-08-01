import {
  ArrowRight,
  CaretLeft,
  CaretRight,
  CheckCircle,
  NumberCircleThree,
  NumberCircleTwo,
  Warning,
} from "@phosphor-icons/react";
import { useState } from "react";
import invoicePreview from "../../../assets/invoice-preview.png";
import { useLanguage } from "../../../i18n/LanguageContext";
import type { DocumentType, ExtractedField } from "../../../types/documents";
import type { Invoice } from "../../../types/invoice";

interface DocumentReviewSectionProps {
  invoice: Invoice;
  onConfirm: () => void;
  isPending?: boolean;
}

const krwFormatter = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "KRW",
  maximumFractionDigits: 0,
});

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
  const needsReview = field.status === "REVIEW_REQUIRED" || field.status === "MISMATCH";
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
              {label === "INVOICE AMOUNT" || label === "인보이스 금액"
                ? t("Matches PO-89341", "PO-89341과 일치")
                : label === "DELIVERY STATUS" || label === "납품 상태"
                  ? t("Evidence matched", "증빙 일치")
                  : t("Auto verified", "자동 검증")}
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
  const selectPreviousDocument = () => {
    if (documentCount > 1) {
      setActiveDocumentIndex((current) => (current - 1 + documentCount) % documentCount);
    }
  };
  const selectNextDocument = () => {
    if (documentCount > 1) {
      setActiveDocumentIndex((current) => (current + 1) % documentCount);
    }
  };
  const longDateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  const buyerName =
    analysis.buyerName.value === "Prime Mobility"
      ? "Prime Mobility Co., Ltd."
      : String(analysis.buyerName.value ?? "Not found");
  const dueDate = analysis.dueDate.value
    ? longDateFormatter.format(new Date(`${analysis.dueDate.value}T00:00:00`))
    : t("Not found", "찾을 수 없음");
  const deliveryDate = longDateFormatter.format(new Date(`${invoice.deliveryDate}T00:00:00`));

  return (
    <section className="document-review-page">
      <header className="review-heading">
        <div>
          <p className="breadcrumb">{t("Invoices / New invoice / Review extraction", "인보이스 / 새 인보이스 / 추출 정보 확인")}</p>
          <h1>{t("Review extracted information", "추출 정보 확인")}</h1>
          <p>{t("Compare the original document with the values found by Document Agent.", "원본 문서와 Document Agent가 찾은 값을 비교하세요.")}</p>
        </div>
        <span className="verification-count">{t("9 of 10 verified", "10개 중 9개 검증")}</span>
      </header>

      <ol className="review-steps" aria-label={t("Invoice verification progress", "인보이스 확인 진행 상황")}>
        <li className="is-complete">
          <CheckCircle aria-hidden="true" size={24} weight="fill" />
          <span>{t("Upload documents", "문서 업로드")}</span>
        </li>
        <li className="is-current">
          <NumberCircleTwo aria-hidden="true" size={24} weight="fill" />
          <span>{t("Review extraction", "추출 정보 확인")}</span>
        </li>
        <li>
          <NumberCircleThree aria-hidden="true" size={24} weight="regular" />
          <span>{t("Request verification", "검증 요청")}</span>
        </li>
      </ol>

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
          <div className="document-review-preview__body">
            <button
              className="document-review-preview__nav"
              type="button"
              onClick={selectPreviousDocument}
              disabled={documentCount < 2}
              aria-label={t("Previous document", "이전 문서")}
            >
              <CaretLeft aria-hidden="true" size={18} weight="bold" />
            </button>
            <div className="document-review-preview__frame">
              {activeDocument?.storageUrl ? (
                <iframe title={activeDocument.fileName} src={activeDocument.storageUrl} />
              ) : (
                <img
                  src={invoicePreview}
                  alt={t(
                    `${activeDocument ? documentTypeLabel(activeDocument.type) : ""} document preview`,
                    `${activeDocument ? documentTypeLabel(activeDocument.type) : ""} 문서 미리보기`,
                  )}
                />
              )}
            </div>
            <button
              className="document-review-preview__nav"
              type="button"
              onClick={selectNextDocument}
              disabled={documentCount < 2}
              aria-label={t("Next document", "다음 문서")}
            >
              <CaretRight aria-hidden="true" size={18} weight="bold" />
            </button>
          </div>
        </section>

        <div className="review-fields">
          <ReviewField label={t("INVOICE ID", "인보이스 ID")} field={analysis.invoiceNumber} value={String(analysis.invoiceNumber.value ?? t("Not found", "찾을 수 없음"))} />
          <ReviewField label={t("BUYER", "구매자")} field={analysis.buyerName} value={buyerName} />
          <ReviewField
            label={t("INVOICE AMOUNT", "인보이스 금액")}
            field={analysis.amountKrw}
            value={analysis.amountKrw.value === null ? t("Not found", "찾을 수 없음") : krwFormatter.format(analysis.amountKrw.value)}
          />
          <ReviewField label={t("DUE DATE", "만기일")} field={analysis.dueDate} value={dueDate} />
          <ReviewField
            label={t("CONTRACT REFERENCE", "계약 참조")}
            field={analysis.contractNumber}
            value={String(analysis.contractNumber.value ?? t("Not found", "찾을 수 없음"))}
            note={t("Two reference candidates were found. Confirm the correct value.", "참조 후보가 두 개 발견되었습니다. 올바른 값을 확인하세요.")}
          />
          <ReviewField
            label={t("DELIVERY STATUS", "납품 상태")}
            field={analysis.deliveryCompleted}
            value={`${analysis.deliveryCompleted.value ? t("Completed", "완료") : t("Not completed", "미완료")} · ${deliveryDate}`}
          />
        </div>
      </div>

      <footer className="review-actions">
        <p>{t("1 item needs your confirmation before sending to the buyer.", "구매자에게 보내기 전에 1개 항목을 확인해야 합니다.")}</p>
        <button className="primary-button review-confirm" type="button" onClick={onConfirm} disabled={isPending}>
          {isPending ? t("Requesting verification...", "검증 요청 중...") : t("Confirm and continue", "확인 후 계속")}
          {!isPending && <ArrowRight aria-hidden="true" size={14} weight="bold" />}
        </button>
      </footer>
    </section>
  );
}
