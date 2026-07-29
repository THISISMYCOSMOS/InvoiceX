import type { BlockchainTransaction } from "../types/agents";
import { ExplorerLink } from "./ExplorerLink";

export function TransactionReceipt({ transaction }: { transaction: BlockchainTransaction }) {
  return <section><h2>Transaction Hash</h2><dl><dt>Hash</dt><dd>{transaction.signature}</dd><dt>상태</dt><dd>{transaction.status}</dd><dt>금액</dt><dd>{transaction.amountUsdc} USDC</dd><dt>발신 주소</dt><dd>{transaction.fromAddress}</dd><dt>수신 주소</dt><dd>{transaction.toAddress}</dd><dt>네트워크</dt><dd>{transaction.network}</dd></dl><ExplorerLink signature={transaction.signature} /></section>;
}
