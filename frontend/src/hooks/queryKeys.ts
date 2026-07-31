export const queryKeys = {
  invoice: (invoiceId: string) => ["invoice", invoiceId] as const,
  invoices: ["invoices"] as const,
  verifications: ["verifications"] as const,
  investorDashboard: ["investorDashboard"] as const,
  investorMandate: ["investorMandate"] as const,
};
