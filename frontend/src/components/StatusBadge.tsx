import { getInvoiceStatusLabel, type InvoiceStatus } from "../types/invoice";

export function StatusBadge({ status }: { status: InvoiceStatus }) {
  return <span aria-label={`상태: ${getInvoiceStatusLabel(status)}`}>{getInvoiceStatusLabel(status)}</span>;
}
