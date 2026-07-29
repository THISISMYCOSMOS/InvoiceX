import { useMutation, useQueryClient } from "@tanstack/react-query";
import { demoApi } from "../api/demo.api";
import { invoiceApi } from "../api/invoices.api";
import { verificationApi } from "../api/verifications.api";
import { settlementApi } from "../api/settlement.api";
import type { Invoice } from "../types/invoice";
import { queryKeys } from "./queryKeys";

function useDemoMutation<TVariables>(mutationFn: (variables: TVariables) => Promise<Invoice>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
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

export function useDemoControl() {
  return {
    reset: useDemoMutation<void>(() => demoApi.reset()),
    analyze: useDemoMutation<string>(invoiceApi.analyzeInvoice),
    requestVerification: useDemoMutation<string>(invoiceApi.requestVerification),
    confirm: useDemoMutation<string>(verificationApi.confirmVerification),
    acceptOffer: useDemoMutation<string>((invoiceId) => invoiceApi.respondToOffer(invoiceId, "ACCEPT")),
    fund: useDemoMutation<string>(invoiceApi.runFunding),
    mockPayment: useDemoMutation<string>(settlementApi.mockPayment),
    settle: useDemoMutation<string>(settlementApi.runSettlement),
  };
}
