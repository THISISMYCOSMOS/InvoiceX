import type { BlockchainTransaction } from "../types/agents";
import { ExplorerLink } from "./ExplorerLink";
import { useLanguage } from "../i18n/LanguageContext";

export function TransactionReceipt({ transaction }: { transaction: BlockchainTransaction }) {
  const { t } = useLanguage();
  return <section><h2>Transaction Hash</h2><dl><dt>Hash</dt><dd>{transaction.signature}</dd><dt>{t("Status", "상태")}</dt><dd>{transaction.status}</dd><dt>{t("Amount", "금액")}</dt><dd>{transaction.amountUsdc} USDC</dd><dt>{t("From address", "발신 주소")}</dt><dd>{transaction.fromAddress}</dd><dt>{t("To address", "수신 주소")}</dt><dd>{transaction.toAddress}</dd><dt>{t("Network", "네트워크")}</dt><dd>{transaction.network}</dd></dl><ExplorerLink signature={transaction.signature} /></section>;
}
