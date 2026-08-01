import type {
  Invoice,
  InvestorDashboard,
  InvestorDeposit,
  InvestorDepositPreparation,
  VerificationRequest,
} from "../../types/invoice";

export type OfferResponse = "ACCEPT" | "DECLINE";

export interface ScenarioAdapter {
  submitInvoiceDocuments(formData: FormData): Promise<Invoice>;
  getInvoices(): Promise<Invoice[]>;
  getInvoice(invoiceId: string): Promise<Invoice>;
  analyzeInvoice(invoiceId: string): Promise<Invoice>;
  requestVerification(invoiceId: string): Promise<Invoice>;
  getVerifications(): Promise<VerificationRequest[]>;
  getVerification(verificationId: string): Promise<VerificationRequest>;
  confirmVerification(verificationId: string): Promise<Invoice>;
  respondToOffer(
    invoiceId: string,
    response: OfferResponse,
    supplierWalletAddress?: string,
  ): Promise<Invoice>;
  runFunding(invoiceId: string): Promise<Invoice>;
  mockPayment(invoiceId: string): Promise<Invoice>;
  runSettlement(invoiceId: string): Promise<Invoice>;
  getInvestorDashboard(): Promise<InvestorDashboard>;
  prepareInvestorDeposit(
    investorWalletAddress: string,
    amountUsdc: number,
  ): Promise<InvestorDepositPreparation>;
  confirmInvestorDeposit(
    referenceId: string,
    signature: string,
  ): Promise<InvestorDeposit>;
  reset(): Promise<Invoice>;
}
