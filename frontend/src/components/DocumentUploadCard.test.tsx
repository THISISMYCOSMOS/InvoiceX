import { render, screen } from "@testing-library/react";
import { test, vi } from "vitest";
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

  expect(screen.getByText("PDF, JPG, PNG · Max 20 MB each")).toBeInTheDocument();
  expect(screen.getByText("Invoice")).toBeInTheDocument();
  expect(screen.getByText("Contract")).toBeInTheDocument();
  expect(screen.getByText("Purchase order")).toBeInTheDocument();
  expect(screen.getByText("Proof of delivery")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze documents" })).toBeDisabled();
});

test("enables analysis when all four valid documents are complete", () => {
  const onAnalyze = vi.fn();
  const fourCompletedDocuments: InvoiceDocument[] = REQUIRED_DOCUMENT_TYPES.map((type, index) => ({
    id: `DOC-${index}`,
    invoiceId: "INV-2026-001",
    type,
    fileName: `${type}.pdf`,
    mimeType: "application/pdf",
    fileSize: 1024,
    uploadStatus: "COMPLETED",
  }));

  render(
    <DocumentUploadCard
      documents={fourCompletedDocuments}
      onFileSelected={vi.fn()}
      onRemove={vi.fn()}
      onAnalyze={onAnalyze}
    />,
  );

  const analyzeButton = screen.getByRole("button", { name: "Analyze documents" });
  expect(analyzeButton).toBeEnabled();
});
