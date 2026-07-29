import { useQuery } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { queryKeys } from "./queryKeys";

export function useInvoice(invoiceId: string) {
  return useQuery({
    queryKey: queryKeys.invoice(invoiceId),
    queryFn: () => invoiceApi.getInvoice(invoiceId),
  });
}
