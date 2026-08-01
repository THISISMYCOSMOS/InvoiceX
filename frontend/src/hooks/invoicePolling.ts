import type { InvoiceStatus } from "../types/invoice";

const processingStatuses: ReadonlySet<InvoiceStatus> = new Set([
  "DOCUMENT_UPLOADING",
  "DOCUMENT_ANALYZING",
  "RISK_ASSESSING",
  "RWA_ISSUED",
  "FUNDING",
  "SETTLING",
]);

export function getInvoicePollingInterval(status: InvoiceStatus | undefined): number | false {
  return status && processingStatuses.has(status) ? 2_000 : false;
}
