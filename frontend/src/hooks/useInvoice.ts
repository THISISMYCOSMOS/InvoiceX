import { useQuery } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { getInvoicePollingInterval } from "./invoicePolling";
import { queryKeys } from "./queryKeys";

export function useInvoice(invoiceId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.invoice(invoiceId),
    queryFn: () => invoiceApi.getInvoice(invoiceId),
    enabled,
    refetchInterval: (query) => getInvoicePollingInterval(query.state.data?.status),
  });
}
