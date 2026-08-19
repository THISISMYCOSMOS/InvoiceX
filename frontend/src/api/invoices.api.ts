import { scenarioAdapter } from "./client";
import type { OfferResponse } from "./adapters/contracts";

export const invoiceApi = {
  submitInvoiceDocuments: (formData: FormData) => scenarioAdapter.submitInvoiceDocuments(formData),
  getInvoices: () => scenarioAdapter.getInvoices(),
  getInvoice: (invoiceId: string) => scenarioAdapter.getInvoice(invoiceId),
  analyzeInvoice: (invoiceId: string) => scenarioAdapter.analyzeInvoice(invoiceId),
  requestVerification: (invoiceId: string) => scenarioAdapter.requestVerification(invoiceId),
  requestRiskReview: (invoiceId: string) => scenarioAdapter.requestRiskReview(invoiceId),
  respondToOffer: (
    invoiceId: string,
    response: OfferResponse,
    supplierWalletAddress?: string,
  ) => scenarioAdapter.respondToOffer(invoiceId, response, supplierWalletAddress),
  runFunding: (invoiceId: string) => scenarioAdapter.runFunding(invoiceId),
};
