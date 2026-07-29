import { useState } from "react";
import { DocumentUploadCard } from "../../components/DocumentUploadCard";
import { ErrorState } from "../../components/ErrorState";
import { DEMO_INVOICE } from "../../mocks/demoScenario";
import { useDocumentAnalysis } from "../../hooks/useDocumentAnalysis";
import type { DocumentType, InvoiceDocument } from "../../types/documents";

export function NewInvoicePage() {
  const [documents, setDocuments] = useState<InvoiceDocument[]>([]);
  const analysis = useDocumentAnalysis();
  const onFileSelected = (type: DocumentType, file: File) => setDocuments((current) => [
    ...current.filter((document) => document.type !== type),
    { id: `LOCAL-${type}`, invoiceId: DEMO_INVOICE.id, type, fileName: file.name, mimeType: file.type, fileSize: file.size, uploadStatus: "COMPLETED" },
  ]);

  return <section><h1>새 인보이스 등록</h1><DocumentUploadCard documents={documents} onFileSelected={onFileSelected} onRemove={(type) => setDocuments((current) => current.filter((document) => document.type !== type))} onAnalyze={() => analysis.mutate(DEMO_INVOICE.id)} isAnalyzing={analysis.isPending} />{analysis.error && <ErrorState error={analysis.error} />}{analysis.isSuccess && <p role="status">분석 결과를 준비했습니다.</p>}</section>;
}
