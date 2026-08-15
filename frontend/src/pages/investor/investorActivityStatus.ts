import type { Invoice } from "../../types/invoice";

export type InvestorActivityFilter = "ALL" | "EXECUTED" | "NOT_EXECUTED" | "IN_REVIEW";

export interface InvestorActivityResult {
  filter: Exclude<InvestorActivityFilter, "ALL">;
  english: string;
  korean: string;
  className: string;
}

export function investorActivityResult(invoice: Pick<Invoice, "agentDecision">): InvestorActivityResult {
  switch (invoice.agentDecision?.status) {
    case "EXECUTED":
      return { filter: "EXECUTED", english: "Investment executed", korean: "투자 실행", className: "investor-result--invested" };
    case "REJECTED":
    case "FAILED":
      return { filter: "NOT_EXECUTED", english: "Investment not executed", korean: "투자 보류", className: "investor-result--excluded" };
    default:
      return { filter: "IN_REVIEW", english: "Under review", korean: "검토 중", className: "investor-result--pending" };
  }
}

export function investorActivityAmount(invoice: Invoice): number {
  return invoice.fundingTransaction?.amountUsdc ?? invoice.agentDecision?.amountUsdc ?? 0;
}

export function investorActivityTime(invoice: Invoice): string | undefined {
  return invoice.fundingTransaction?.createdAt ?? invoice.agentDecision?.createdAt;
}

export function investorActivityReason(invoice: Invoice, english: string, korean: string): string {
  return invoice.agentDecision?.reason ?? (invoice.agentDecision?.status === "EXECUTED"
    ? english
    : korean);
}
