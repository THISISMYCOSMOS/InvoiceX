import { useQuery } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { queryKeys } from "./queryKeys";

export function useInvoices(enabled = true) {
  return useQuery({
    queryKey: queryKeys.invoices,
    queryFn: invoiceApi.getInvoices,
    enabled,
  });
}
