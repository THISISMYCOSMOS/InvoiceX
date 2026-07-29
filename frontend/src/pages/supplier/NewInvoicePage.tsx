import { useState } from "react";
import { DocumentUploadCard } from "../../components/DocumentUploadCard";
import { ErrorState } from "../../components/ErrorState";
import { DEMO_INVOICE } from "../../mocks/demoScenario";
import { useDocumentUpload } from "../../hooks/useDocumentUpload";
import type { DocumentType, InvoiceDocument } from "../../types/documents";

export function NewInvoicePage() {
  const [documents, setDocuments] = useState<InvoiceDocument[]>([]);
  const [files, setFiles] = useState<Partial<Record<DocumentType, File>>>({});
  const upload = useDocumentUpload();
  const onFileSelected = (type: DocumentType, file: File) => {
    setFiles((current) => ({ ...current, [type]: file }));
    setDocuments((current) => [...current.filter((document) => document.type !== type), { id: `LOCAL-${type}`, invoiceId: DEMO_INVOICE.id, type, fileName: file.name, mimeType: file.type, fileSize: file.size, uploadStatus: "COMPLETED" }]);
  };
  const onAnalyze = () => {
    const formData = new FormData();
    Object.entries(files).forEach(([type, file]) => {
      if (file) formData.append(type, file);
    });
    upload.mutate(formData);
  };

  return <section><h1>새 인보이스 등록</h1><DocumentUploadCard documents={documents} onFileSelected={onFileSelected} onRemove={(type) => { setFiles((current) => { const next = { ...current }; delete next[type]; return next; }); setDocuments((current) => current.filter((document) => document.type !== type)); }} onAnalyze={onAnalyze} isAnalyzing={upload.isPending} />{upload.error && <ErrorState error={upload.error} />}{upload.isSuccess && <p role="status">문서 등록과 분석 요청을 완료했습니다.</p>}</section>;
}
