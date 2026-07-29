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
  const confirmInvoice = useDemoMutation<string>(async (invoiceId) => {
    const current = await invoiceApi.getInvoice(invoiceId);
    if (current.status === "DOCUMENT_REVIEW_REQUIRED") {
      const requested = await invoiceApi.requestVerification(invoiceId);
      if (!requested.verificationId) {
        throw new Error("검증 요청 ID가 생성되지 않았습니다.");
      }
      return verificationApi.confirmVerification(requested.verificationId);
    }
    if (current.status === "BUYER_REVIEW" && current.verificationId) {
      return verificationApi.confirmVerification(current.verificationId);
    }
    throw new Error("Buyer Confirm을 실행할 수 있는 상태가 아닙니다.");
  });

  return {
    reset: useDemoMutation<void>(() => demoApi.reset()),
    analyze: useDemoMutation<string>(invoiceApi.analyzeInvoice),
    requestVerification: useDemoMutation<string>(invoiceApi.requestVerification),
    confirm: confirmInvoice,
    generateRiskPassport: useDemoMutation<string>(invoiceApi.getInvoice),
    acceptOffer: useDemoMutation<string>((invoiceId) => invoiceApi.respondToOffer(invoiceId, "ACCEPT")),
    fund: useDemoMutation<string>(invoiceApi.runFunding),
    mockPayment: useDemoMutation<string>(settlementApi.mockPayment),
    settle: useDemoMutation<string>(settlementApi.runSettlement),
  };
}
