import { useState } from "react";
import { REQUIRED_DOCUMENT_TYPES } from "../mocks/demoScenario";
import type { DocumentType, InvoiceDocument } from "../types/documents";
import { validateDocumentFile } from "../utils/fileValidation";

const labels: Record<DocumentType, string> = {
  INVOICE: "인보이스",
  CONTRACT: "계약서",
  PURCHASE_ORDER: "발주서 또는 PO",
  DELIVERY_PROOF: "납품·용역 완료 증빙",
};

interface DocumentUploadCardProps {
  documents: InvoiceDocument[];
  onFileSelected: (type: DocumentType, file: File) => void;
  onRemove: (type: DocumentType) => void;
  onAnalyze: () => void;
  isAnalyzing?: boolean;
}

export function DocumentUploadCard({ documents, onFileSelected, onRemove, onAnalyze, isAnalyzing = false }: DocumentUploadCardProps) {
  const [errors, setErrors] = useState<Partial<Record<DocumentType, string>>>({});
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
    <section aria-label="필수 문서 업로드">
      <h2>문서 등록</h2>
      {REQUIRED_DOCUMENT_TYPES.map((type) => {
        const document = documents.find((item) => item.type === type);
        return (
          <fieldset key={type} onDrop={(event) => { event.preventDefault(); selectFile(type, event.dataTransfer.files[0]); }} onDragOver={(event) => event.preventDefault()}>
            <legend>{labels[type]}</legend>
            <label>
              {labels[type]} 파일 선택
              <input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={(event) => selectFile(type, event.currentTarget.files?.[0])} />
            </label>
            <p>{document ? `${document.fileName} — ${document.uploadStatus}` : "파일을 선택하거나 여기로 끌어오세요."}</p>
            {document && <button type="button" onClick={() => onRemove(type)}>파일 제거</button>}
            {errors[type] && <p role="alert">{errors[type]}</p>}
          </fieldset>
        );
      })}
      <button type="button" disabled={!canAnalyze || isAnalyzing} onClick={onAnalyze}>Document Agent 분석 실행</button>
    </section>
  );
}
