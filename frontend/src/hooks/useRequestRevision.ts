import { useMutation, useQueryClient } from "@tanstack/react-query";
import { verificationApi } from "../api/verifications.api";
import { queryKeys } from "./queryKeys";

export function useRequestRevision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: verificationApi.requestRevision,
    onSuccess: async (invoice) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.invoice(invoice.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.invoices }),
        queryClient.invalidateQueries({ queryKey: queryKeys.verifications }),
      ]);
    },
  });
}
