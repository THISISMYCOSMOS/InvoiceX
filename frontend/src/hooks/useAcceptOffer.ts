import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import type { OfferResponse } from "../api/adapters/contracts";
import { queryKeys } from "./queryKeys";

export function useAcceptOffer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      invoiceId,
      response,
      supplierWalletAddress,
    }: {
      invoiceId: string;
      response: OfferResponse;
      supplierWalletAddress?: string;
    }) => invoiceApi.respondToOffer(invoiceId, response, supplierWalletAddress),
    onSuccess: async (invoice) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.invoice(invoice.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.invoices }),
      ]);
    },
  });
}
