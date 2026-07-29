import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { queryKeys } from "./queryKeys";

export function useDocumentAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: invoiceApi.analyzeInvoice,
    onSuccess: async (invoice) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.invoice(invoice.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.invoices }),
      ]);
    },
  });
}
