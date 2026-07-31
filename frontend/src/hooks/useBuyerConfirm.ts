import { useMutation, useQueryClient } from "@tanstack/react-query";
import { verificationApi } from "../api/verifications.api";
import { queryKeys } from "./queryKeys";
import type { BuyerChecklist } from "../types/invoice";

export function useBuyerConfirm() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ verificationId, checklist }: { verificationId: string; checklist: BuyerChecklist }) =>
      verificationApi.confirmVerification(verificationId, checklist),
    onSuccess: async (invoice) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.invoice(invoice.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.invoices }),
        queryClient.invalidateQueries({ queryKey: queryKeys.verifications }),
        queryClient.invalidateQueries({ queryKey: queryKeys.investorDashboard }),
      ]);
    },
  });
}
