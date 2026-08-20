import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { queryKeys } from "./queryKeys";
import { waitForDocumentReview } from "./waitForDocumentReview";

export function useDocumentReplacement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ invoiceId, formData }: { invoiceId: string; formData: FormData }) => {
      const invoice = await invoiceApi.replaceInvoiceDocuments(invoiceId, formData);
      return waitForDocumentReview(invoice, invoiceApi.getInvoice);
    },
    onSuccess: async (invoice) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.invoice(invoice.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.invoices }),
      ]);
    },
  });
}
