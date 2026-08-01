import type { BlockchainTransaction } from "../types/agents";
import { ExplorerLink } from "./ExplorerLink";
import { useLanguage } from "../i18n/LanguageContext";

export function TransactionReceipt({ transaction }: { transaction: BlockchainTransaction }) {
  const { t } = useLanguage();
  return (
    <section className="transaction-receipt" aria-label={t("Settlement transaction receipt", "정산 트랜잭션 영수증")}>
      <header>
        <div>
          <span>{t("ON-CHAIN RECEIPT", "온체인 지급 영수증")}</span>
          <h2>{t("Transaction details", "트랜잭션 상세")}</h2>
        </div>
        <strong className={`transaction-receipt__status transaction-receipt__status--${transaction.status.toLowerCase()}`}>{transaction.status}</strong>
      </header>
      <dl>
        <div className="transaction-receipt__signature"><dt>{t("Transaction signature", "트랜잭션 해시")}</dt><dd>{transaction.signature}</dd></div>
        <div><dt>{t("Amount", "지급 금액")}</dt><dd>{transaction.amountUsdc.toLocaleString()} USDC</dd></div>
        <div><dt>{t("From address", "발신 주소")}</dt><dd>{transaction.fromAddress}</dd></div>
        <div><dt>{t("To address", "수신 주소")}</dt><dd>{transaction.toAddress}</dd></div>
        <div><dt>{t("Network", "네트워크")}</dt><dd>{transaction.network.replace("_", " · ")}</dd></div>
      </dl>
      <footer><ExplorerLink signature={transaction.signature} /></footer>
    </section>
  );
}
