import { scenarioAdapter } from "./client";

export const settlementApi = {
  mockPayment: (invoiceId: string) => scenarioAdapter.mockPayment(invoiceId),
  runSettlement: (invoiceId: string) => scenarioAdapter.runSettlement(invoiceId),
};
