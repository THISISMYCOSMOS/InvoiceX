import { getInvoiceStatusLabel, type InvoiceStatus } from "../types/invoice";

export function StatusBadge({ status }: { status: InvoiceStatus }) {
  return <span className="ml-2 inline-flex rounded-full bg-invoicex-50 px-2.5 py-1 text-xs font-semibold text-invoicex-700" aria-label={`상태: ${getInvoiceStatusLabel(status)}`}>{getInvoiceStatusLabel(status)}</span>;
}
