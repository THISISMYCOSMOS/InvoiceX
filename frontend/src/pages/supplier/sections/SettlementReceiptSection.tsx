import { TransactionReceipt } from "../../../components/TransactionReceipt";
import type { Invoice } from "../../../types/invoice";

export function SettlementReceiptSection({ invoice }: { invoice: Invoice }) {
  return <section><h2>만기 정산 완료</h2>{invoice.settlement && <dl><dt>투자기관 수령</dt><dd>{invoice.settlement.investorSettlementUsdc} USDC</dd><dt>플랫폼 수수료</dt><dd>{invoice.settlement.platformFeeUsdc} USDC</dd></dl>}{invoice.settlementTransaction && <TransactionReceipt transaction={invoice.settlementTransaction} />}</section>;
}
