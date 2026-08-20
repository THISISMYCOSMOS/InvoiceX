import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { DocumentUploadCard } from "../../components/DocumentUploadCard";
import { DocumentAnalysisLoadingScreen } from "../../components/DocumentAnalysisLoadingScreen";
import { ErrorState } from "../../components/ErrorState";
import { InvoiceRegistrationProgress } from "../../components/InvoiceRegistrationProgress";
import { isMockApi } from "../../api/client";
import { useDocumentUpload } from "../../hooks/useDocumentUpload";
import { useDocumentReplacement } from "../../hooks/useDocumentReplacement";
import type { DocumentType, InvoiceDocument } from "../../types/documents";
import { useLanguage } from "../../i18n/LanguageContext";

export function NewInvoicePage() {
  const [documents, setDocuments] = useState<InvoiceDocument[]>([]);
  const [files, setFiles] = useState<Partial<Record<DocumentType, File>>>({});
  const upload = useDocumentUpload();
  const replacement = useDocumentReplacement();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useLanguage();
  const invoiceIdToReplace = searchParams.get("replace");
  const isReplacing = Boolean(invoiceIdToReplace);
  const isAnalyzing = upload.isPending || replacement.isPending;
  const onFileSelected = (type: DocumentType, file: File) => {
    setFiles((current) => ({ ...current, [type]: file }));
    setDocuments((current) => [...current.filter((document) => document.type !== type), { id: `LOCAL-${type}`, invoiceId: "LOCAL-DRAFT", type, fileName: file.name, mimeType: file.type, fileSize: file.size, uploadStatus: "COMPLETED" }]);
  };
  const onAnalyze = () => {
    const formData = new FormData();
    Object.entries(files).forEach(([type, file]) => {
      if (file) formData.append(type, file);
    });
    const onSuccess = (invoice: { id: string }) => navigate(`/supplier/invoices/${invoice.id}`);
    if (invoiceIdToReplace) {
      replacement.mutate({ invoiceId: invoiceIdToReplace, formData }, { onSuccess });
      return;
    }
    upload.mutate(formData, {
      onSuccess,
    });
  };
  const onQuickRegister = () => {
    upload.mutate(new FormData(), {
      onSuccess: (invoice) => navigate(`/supplier/invoices/${invoice.id}`),
    });
  };

  if (isAnalyzing) {
    return <DocumentAnalysisLoadingScreen />;
  }

  return (
    <section className="new-invoice-page">
      <header className="new-invoice-heading">
        <div>
          <h1>{isReplacing ? t("Replace invoice documents", "인보이스 문서 수정") : t("Register a new invoice", "새 인보이스 등록")}</h1>
          <p>{isReplacing
            ? t("Select all replacement documents. The previous extraction will be discarded and analyzed again.", "교체할 문서를 모두 선택하세요. 기존 추출 결과는 폐기되고 다시 분석됩니다.")
            : isMockApi
            ? t("Register a ready-made sample invoice to preview the workflow.", "샘플 인보이스를 바로 등록해 전체 흐름을 빠르게 확인하세요.")
            : t("Upload the documents required to verify your transaction.", "거래 검증에 필요한 문서를 업로드하세요.")}</p>
        </div>
        <span className="draft-badge">{t("Draft saved", "초안 저장됨")}</span>
      </header>
      <InvoiceRegistrationProgress step={1} />
      {isMockApi && !isReplacing ? (
        <section className="demo-invoice-registration">
          <div>
            <span>{t("DEMO MODE", "목업 모드")}</span>
            <h2>{t("Register a sample invoice instantly", "샘플 인보이스를 바로 등록하세요")}</h2>
            <p>{t("A prepared document set and extracted data will be added for this frontend preview.", "프론트엔드 미리보기를 위한 문서 세트와 추출 정보가 즉시 등록됩니다.")}</p>
          </div>
          <button type="button" className="primary-button" disabled={upload.isPending} onClick={onQuickRegister}>
            {upload.isPending ? t("Registering…", "등록 중…") : t("Register demo invoice", "데모 인보이스 바로 등록")}
          </button>
        </section>
      ) : (
        <DocumentUploadCard
          documents={documents}
          onFileSelected={onFileSelected}
          onRemove={(type) => {
            setFiles((current) => {
              const next = { ...current };
              delete next[type];
              return next;
            });
            setDocuments((current) => current.filter((document) => document.type !== type));
          }}
          onAnalyze={onAnalyze}
          isAnalyzing={isAnalyzing}
        />
      )}
      {(upload.error || replacement.error) && <ErrorState error={upload.error ?? replacement.error} />}
    </section>
  );
}
