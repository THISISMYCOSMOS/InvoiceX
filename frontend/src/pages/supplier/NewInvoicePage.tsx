import { useState } from "react";
import { useNavigate } from "react-router";
import { DocumentUploadCard } from "../../components/DocumentUploadCard";
import { ErrorState } from "../../components/ErrorState";
import { DEMO_INVOICE } from "../../mocks/demoScenario";
import { useDocumentUpload } from "../../hooks/useDocumentUpload";
import type { DocumentType, InvoiceDocument } from "../../types/documents";
import { useLanguage } from "../../i18n/LanguageContext";

export function NewInvoicePage() {
  const [documents, setDocuments] = useState<InvoiceDocument[]>([]);
  const [files, setFiles] = useState<Partial<Record<DocumentType, File>>>({});
  const upload = useDocumentUpload();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const onFileSelected = (type: DocumentType, file: File) => {
    setFiles((current) => ({ ...current, [type]: file }));
    setDocuments((current) => [...current.filter((document) => document.type !== type), { id: `LOCAL-${type}`, invoiceId: DEMO_INVOICE.id, type, fileName: file.name, mimeType: file.type, fileSize: file.size, uploadStatus: "COMPLETED" }]);
  };
  const onAnalyze = () => {
    const formData = new FormData();
    Object.entries(files).forEach(([type, file]) => {
      if (file) formData.append(type, file);
    });
    upload.mutate(formData, {
      onSuccess: (invoice) => navigate(`/supplier/invoices/${invoice.id}`),
    });
  };

  return (
    <section className="new-invoice-page">
      <header className="new-invoice-heading">
        <div>
          <p className="breadcrumb">{t("Invoices / New invoice", "인보이스 / 새 인보이스")}</p>
          <h1>{t("Register a new invoice", "새 인보이스 등록")}</h1>
          <p>{t("Upload the documents required to verify your transaction.", "거래 검증에 필요한 문서를 업로드하세요.")}</p>
        </div>
        <span className="draft-badge">{t("Draft saved", "초안 저장됨")}</span>
      </header>
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
        isAnalyzing={upload.isPending}
      />
      {upload.error && <ErrorState error={upload.error} />}
    </section>
  );
}
