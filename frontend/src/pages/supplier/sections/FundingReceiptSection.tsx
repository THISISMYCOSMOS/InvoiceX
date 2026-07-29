import { TransactionReceipt } from "../../../components/TransactionReceipt";
import type { Invoice } from "../../../types/invoice";

export function FundingReceiptSection({ invoice }: { invoice: Invoice }) {
  return <section><h2>USDC 지급 완료</h2>{invoice.fundingTransaction && <TransactionReceipt transaction={invoice.fundingTransaction} />}</section>;
}
