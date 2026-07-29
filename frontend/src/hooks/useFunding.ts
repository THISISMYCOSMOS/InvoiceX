import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { queryKeys } from "./queryKeys";

export function useFunding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: invoiceApi.runFunding,
    onSuccess: async (invoice) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.invoice(invoice.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.invoices }),
        queryClient.invalidateQueries({ queryKey: queryKeys.investorDashboard }),
      ]);
    },
  });
}
