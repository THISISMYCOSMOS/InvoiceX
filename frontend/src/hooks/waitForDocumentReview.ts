import type { Invoice } from "../types/invoice";

const analysisStatuses = new Set(["DOCUMENT_UPLOADING", "DOCUMENT_ANALYZING"]);

export async function waitForDocumentReview(
  initialInvoice: Invoice,
  getInvoice: (invoiceId: string) => Promise<Invoice>,
  options: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<Invoice> {
  const intervalMs = options.intervalMs ?? 2_000;
  const timeoutMs = options.timeoutMs ?? 4 * 60_000;
  const deadline = Date.now() + timeoutMs;
  let invoice = initialInvoice;

  while (invoice.status !== "DOCUMENT_REVIEW_REQUIRED") {
    if (invoice.status === "ERROR" || invoice.status === "BLOCKED") {
      throw new Error("인보이스 문서 분석을 완료하지 못했습니다. 업로드한 문서를 확인해 주세요.");
    }
    if (!analysisStatuses.has(invoice.status)) {
      throw new Error(`문서 분석 중 예상하지 못한 상태가 반환되었습니다: ${invoice.status}`);
    }
    if (Date.now() >= deadline) {
      throw new Error("인보이스 문서 분석 시간이 초과되었습니다. 다시 시도해 주세요.");
    }

    await new Promise<void>((resolve) => window.setTimeout(resolve, intervalMs));
    invoice = await getInvoice(invoice.id);
  }

  return invoice;
}
