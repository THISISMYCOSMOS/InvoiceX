import type { Invoice } from "../types/invoice";

export interface SupplierWalletSummary {
  /** The address the backend actually transfers early-settlement USDC to. */
  address?: string;
  /** USDC that really landed on chain, not a display constant. */
  receivedUsdc: number;
  settledCount: number;
  inProgressCount: number;
  awaitingBuyerCount: number;
}

const IN_PROGRESS = new Set([
  "DOCUMENT_ANALYZING",
  "DOCUMENT_REVIEW_REQUIRED",
  "RISK_ASSESSING",
  "OFFER_READY",
  "FUNDING",
]);

export function supplierWalletSummary(invoices: Invoice[]): SupplierWalletSummary {
  return {
    address: invoices.find((invoice) => invoice.supplier.walletAddress)?.supplier.walletAddress,
    receivedUsdc: invoices.reduce((total, invoice) => {
      const funding = invoice.fundingTransaction;
      return funding?.status === "CONFIRMED" ? total + funding.amountUsdc : total;
    }, 0),
    settledCount: invoices.filter((invoice) => invoice.status === "SETTLED").length,
    inProgressCount: invoices.filter((invoice) => IN_PROGRESS.has(invoice.status)).length,
    awaitingBuyerCount: invoices.filter((invoice) => invoice.status === "BUYER_REVIEW").length,
  };
}
