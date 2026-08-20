import { useMutation, useQueryClient } from "@tanstack/react-query";
import { invoiceApi } from "../api/invoices.api";
import { queryKeys } from "./queryKeys";
import { waitForDocumentReview } from "./waitForDocumentReview";

export function useDocumentUpload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (formData: FormData) => {
      const invoice = await invoiceApi.submitInvoiceDocuments(formData);
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
