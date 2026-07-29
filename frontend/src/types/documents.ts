export type DocumentType =
  | "INVOICE"
  | "CONTRACT"
  | "PURCHASE_ORDER"
  | "DELIVERY_PROOF";

export type UploadStatus = "IDLE" | "UPLOADING" | "COMPLETED" | "FAILED";

export interface InvoiceDocument {
  id: string;
  invoiceId: string;
  type: DocumentType;
  fileName: string;
  mimeType: string;
  fileSize: number;
  storageUrl?: string;
  uploadStatus: UploadStatus;
}

export interface ExtractedField<T> {
  value: T | null;
  evidence?: {
    documentType: DocumentType;
    page: number | null;
    text: string | null;
  };
  status: "MATCHED" | "MISMATCH" | "MISSING" | "REVIEW_REQUIRED";
}

export interface DocumentAnalysis {
  invoiceId: string;
  status: "PENDING" | "ANALYZING" | "COMPLETED" | "FAILED";
  invoiceNumber: ExtractedField<string>;
  supplierName: ExtractedField<string>;
  buyerName: ExtractedField<string>;
  amountKrw: ExtractedField<number>;
  dueDate: ExtractedField<string>;
  contractNumber: ExtractedField<string>;
  purchaseOrderNumber: ExtractedField<string>;
  deliveryCompleted: ExtractedField<boolean>;
  modelName?: string;
  promptVersion?: string;
  analyzedAt?: string;
}
