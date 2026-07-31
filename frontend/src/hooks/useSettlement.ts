import { useMutation, useQueryClient } from "@tanstack/react-query";
import { settlementApi } from "../api/settlement.api";
import { queryKeys } from "./queryKeys";

function useInvoiceSettlementMutation(mutationFn: (invoiceId: string) => Promise<unknown>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: async (invoice) => {
      const currentInvoice = invoice as { id: string };
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.invoice(currentInvoice.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.invoices }),
        queryClient.invalidateQueries({ queryKey: queryKeys.investorDashboard }),
      ]);
    },
  });
}

export function useMockPayment() {
  return useInvoiceSettlementMutation(settlementApi.mockPayment);
}

export function useSettlement() {
  return useInvoiceSettlementMutation(settlementApi.runSettlement);
}
