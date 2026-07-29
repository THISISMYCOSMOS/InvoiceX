import { scenarioAdapter } from "./client";
import type { OfferResponse } from "./adapters/contracts";

export const invoiceApi = {
  submitInvoiceDocuments: (formData: FormData) => scenarioAdapter.submitInvoiceDocuments(formData),
  getInvoices: () => scenarioAdapter.getInvoices(),
  getInvoice: (invoiceId: string) => scenarioAdapter.getInvoice(invoiceId),
  analyzeInvoice: (invoiceId: string) => scenarioAdapter.analyzeInvoice(invoiceId),
  requestVerification: (invoiceId: string) => scenarioAdapter.requestVerification(invoiceId),
  respondToOffer: (invoiceId: string, response: OfferResponse) => scenarioAdapter.respondToOffer(invoiceId, response),
  runFunding: (invoiceId: string) => scenarioAdapter.runFunding(invoiceId),
};
