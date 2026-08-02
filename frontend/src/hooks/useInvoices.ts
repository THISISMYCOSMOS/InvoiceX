import { useQuery } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import type { Invoice } from "../types/invoice";
import { queryKeys } from "./queryKeys";

function normalizedSourceReference(invoice: Invoice) {
  const extractedReference = invoice.analysis?.invoiceNumber.value?.trim();
  if (extractedReference) return `reference:${extractedReference.toLowerCase()}`;

  const invoiceDocument = invoice.documents.find((document) => document.type === "INVOICE");
  if (invoiceDocument?.fileName) return `file:${invoiceDocument.fileName.trim().toLowerCase()}`;

  return `record:${invoice.id}`;
}

export function getInvoiceDisplayReference(invoice: Invoice) {
  return invoice.analysis?.invoiceNumber.value?.trim() || invoice.id;
}

export function deduplicateInvoicesBySourceReference(invoices: Invoice[]) {
  const seen = new Set<string>();
  return invoices.filter((invoice) => {
    const reference = normalizedSourceReference(invoice);
    if (seen.has(reference)) return false;
    seen.add(reference);
    return true;
  });
}

export function useInvoices() {
  return useQuery({
    queryKey: queryKeys.invoices,
    queryFn: invoiceApi.getInvoices,
    select: deduplicateInvoicesBySourceReference,
  });
}
