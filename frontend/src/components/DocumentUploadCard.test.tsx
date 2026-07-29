import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { REQUIRED_DOCUMENT_TYPES } from "../mocks/demoScenario";
import type { InvoiceDocument } from "../types/documents";
import { DocumentUploadCard } from "./DocumentUploadCard";

const threeCompletedDocuments: InvoiceDocument[] = REQUIRED_DOCUMENT_TYPES.slice(0, 3).map((type, index) => ({
  id: `DOC-${index}`,
  invoiceId: "INV-2026-001",
  type,
  fileName: `${type}.pdf`,
  mimeType: "application/pdf",
  fileSize: 1024,
  uploadStatus: "COMPLETED",
}));

test("disables analysis until all four valid documents are complete", () => {
  render(
    <DocumentUploadCard
      documents={threeCompletedDocuments}
      onFileSelected={vi.fn()}
      onRemove={vi.fn()}
      onAnalyze={vi.fn()}
    />,
  );

  expect(screen.getByRole("button", { name: "Document Agent 분석 실행" })).toBeDisabled();
});
