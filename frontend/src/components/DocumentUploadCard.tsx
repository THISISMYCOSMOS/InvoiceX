import { useState } from "react";
import { ArrowRight, Check, File, UploadSimple, X } from "@phosphor-icons/react";
import { REQUIRED_DOCUMENT_TYPES } from "../mocks/demoScenario";
import type { DocumentType, InvoiceDocument } from "../types/documents";
import { validateDocumentFile } from "../utils/fileValidation";
import { useLanguage } from "../i18n/LanguageContext";

const labels: Record<DocumentType, string> = {
  INVOICE: "Invoice",
  CONTRACT: "Contract",
  PURCHASE_ORDER: "Purchase order",
  DELIVERY_PROOF: "Proof of delivery",
};

function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

interface DocumentUploadCardProps {
  documents: InvoiceDocument[];
  onFileSelected: (type: DocumentType, file: File) => void;
  onRemove: (type: DocumentType) => void;
  onAnalyze: () => void;
  isAnalyzing?: boolean;
}

export function DocumentUploadCard({ documents, onFileSelected, onRemove, onAnalyze, isAnalyzing = false }: DocumentUploadCardProps) {
  const [errors, setErrors] = useState<Partial<Record<DocumentType, string>>>({});
  const { language, t } = useLanguage();
  const completedTypes = new Set(documents.filter((document) => document.uploadStatus === "COMPLETED").map((document) => document.type));
  const canAnalyze = REQUIRED_DOCUMENT_TYPES.every((type) => completedTypes.has(type));

  const selectFile = (type: DocumentType, file: File | undefined) => {
    if (!file) return;
    const result = validateDocumentFile(file);
    if (!result.valid) {
      setErrors((current) => ({ ...current, [type]: result.message }));
      return;
    }
    setErrors((current) => ({ ...current, [type]: undefined }));
    onFileSelected(type, file);
  };

  return (
    <section className="document-upload-card" aria-label={t("Required document upload", "필수 문서 업로드")}>
      <header className="document-upload-card__header">
        <h2>{t("Required documents", "필수 문서")}</h2>
        <p>{t("PDF, JPG, PNG · Max 20 MB each", "PDF, JPG, PNG · 파일당 최대 20MB")}</p>
      </header>

      <div className="upload-grid">
        {REQUIRED_DOCUMENT_TYPES.map((type) => {
          const document = documents.find((item) => item.type === type);
          const inputId = `document-${type.toLowerCase()}`;
          return (
            <div
              className={`upload-slot ${document ? "is-complete" : ""}`}
              key={type}
              onDrop={(event) => { event.preventDefault(); selectFile(type, event.dataTransfer.files[0]); }}
              onDragOver={(event) => event.preventDefault()}
            >
              <span className="upload-slot__icon" aria-hidden="true">
                <File size={22} weight="regular" />
              </span>
              <div className="upload-slot__copy">
                <strong>{language === "ko"
                  ? ({ INVOICE: "인보이스", CONTRACT: "계약서", PURCHASE_ORDER: "구매주문서", DELIVERY_PROOF: "납품 증빙" } as Record<DocumentType, string>)[type]
                  : labels[type]}</strong>
                <span>{document ? `${document.fileName} · ${formatFileSize(document.fileSize)}` : t("Drop file here or browse", "파일을 끌어놓거나 찾아보기")}</span>
                {errors[type] && <span className="upload-slot__error" role="alert">{errors[type]}</span>}
              </div>

              <label className={document ? "upload-slot__replace" : "secondary-button upload-slot__button"} htmlFor={inputId}>
                {document ? <span className="sr-only">{t(`Replace ${labels[type]}`, `${labels[type]} 교체`)}</span> : (
                  <>
                    <UploadSimple aria-hidden="true" size={14} />
                    {t("Upload", "업로드")}
                  </>
                )}
              </label>
              <input
                className="sr-only"
                id={inputId}
                aria-label={t(`${labels[type]} file`, `${labels[type]} 파일`)}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                onChange={(event) => selectFile(type, event.currentTarget.files?.[0])}
              />

              {document && (
                <>
                  <Check className="upload-slot__check" aria-hidden="true" size={17} weight="bold" />
                  <button className="upload-slot__remove" type="button" aria-label={t(`Remove ${labels[type]}`, `${labels[type]} 제거`)} onClick={() => onRemove(type)}>
                    <X aria-hidden="true" size={12} weight="bold" />
                  </button>
                </>
              )}
            </div>
          );
        })}
      </div>

      <footer className="document-upload-card__footer">
        <p>{t("All required files must be uploaded before analysis.", "분석 전에 모든 필수 파일을 업로드해야 합니다.")}</p>
        <button className="primary-button analyze-button" type="button" disabled={!canAnalyze || isAnalyzing} onClick={onAnalyze}>
          {isAnalyzing ? t("Analyzing documents...", "문서 분석 중...") : t("Analyze documents", "문서 분석")}
          {!isAnalyzing && <ArrowRight aria-hidden="true" size={14} weight="bold" />}
        </button>
      </footer>
    </section>
  );
}
