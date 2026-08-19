import { useMutation, useQueryClient } from "@tanstack/react-query";
import { verificationApi } from "../api/verifications.api";
import type { BuyerRejectionReason } from "../types/invoice";
import { queryKeys } from "./queryKeys";

export function useBuyerReject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      verificationId,
      reasonCode,
      detail,
    }: {
      verificationId: string;
      reasonCode: BuyerRejectionReason;
      detail?: string;
    }) => verificationApi.rejectVerification(verificationId, reasonCode, detail),
    onSuccess: async (invoice) => {
      queryClient.setQueryData(queryKeys.invoice(invoice.id), invoice);
      await queryClient.invalidateQueries({ queryKey: queryKeys.invoices });
      await queryClient.invalidateQueries({ queryKey: queryKeys.verifications });
    },
  });
}
