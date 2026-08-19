import { Coins, Wallet } from "@phosphor-icons/react";
import { TransactionReceipt } from "../../../components/TransactionReceipt";
import { useLanguage } from "../../../i18n/LanguageContext";
import type { Invoice } from "../../../types/invoice";

export function FundingReceiptSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  const transaction = invoice.fundingTransaction;
  const offeredAmount = invoice.riskPassport?.suggestedAdvanceAmountUsdc;
  const amount = transaction?.amountUsdc ?? offeredAmount;
  const shortenAddress = (address?: string) => address && address.length > 12
    ? `${address.slice(0, 6)}...${address.slice(-4)}`
    : address ?? "—";

  return (
    <section className="funding-receipt">
      <header className="funding-receipt__heading">
        <div>
          <p className="detail-breadcrumb">
            {t("Invoices", "인보이스")} / {invoice.id} / {t("Funding complete", "지급 완료")}
          </p>
          <h1>{t("Maturity settlement completed", "만기 정산이 완료되었습니다")}</h1>
        </div>
      </header>

      <div className="funding-receipt__summary">
        <article className="funding-receipt__amount">
          <span className="funding-receipt__icon">
            <Coins size={24} weight="fill" aria-hidden="true" />
          </span>
          <div>
            <span>{t("Settlement received", "정산 수령액")}</span>
            <strong>{amount?.toLocaleString() ?? "—"} <small>USDC</small></strong>
          </div>
        </article>
        <dl className="funding-receipt__details">
          <div><dt>{t("Invoice", "인보이스")}</dt><dd>{invoice.id}</dd></div>
          <div><dt>{t("From", "지급 출처")}</dt><dd>{shortenAddress(transaction?.fromAddress ?? invoice.investor.vaultAddress)}</dd></div>
          <div><dt>{t("To", "수령 지갑")}</dt><dd><Wallet size={13} weight="fill" aria-hidden="true" /> {shortenAddress(transaction?.toAddress ?? invoice.supplier.walletAddress)}</dd></div>
          <div><dt>{t("Network", "네트워크")}</dt><dd>Solana Devnet</dd></div>
        </dl>
      </div>

      {transaction ? <TransactionReceipt transaction={transaction} /> : null}
    </section>
  );
}
