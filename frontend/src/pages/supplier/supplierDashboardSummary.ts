import type { Invoice, InvoiceStatus } from "../../types/invoice";

const earlySettlementStatuses = new Set<InvoiceStatus>([
  "RISK_ASSESSING",
  "OFFER_READY",
  "REVIEW_REQUESTED",
  "RWA_ISSUED",
  "FUNDING",
]);

export function getDashboardSummary(invoices: Invoice[], currentWalletAddress?: string) {
  return invoices.reduce(
    (summary, invoice) => ({
      earlySettlementInProgress: summary.earlySettlementInProgress
        + (earlySettlementStatuses.has(invoice.status) ? 1 : 0),
      waitingForBuyer: summary.waitingForBuyer + (invoice.status === "BUYER_REVIEW" ? 1 : 0),
      settlementReceivedUsdc: summary.settlementReceivedUsdc
        + (
          invoice.fundingTransaction?.status === "CONFIRMED"
          && invoice.fundingTransaction.toAddress === currentWalletAddress
            ? invoice.fundingTransaction.amountUsdc
            : 0
        ),
    }),
    { earlySettlementInProgress: 0, waitingForBuyer: 0, settlementReceivedUsdc: 0 },
  );
}
