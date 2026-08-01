import { CheckCircle, Coins, Wallet } from "@phosphor-icons/react";
import { TransactionReceipt } from "../../../components/TransactionReceipt";
import { useLanguage } from "../../../i18n/LanguageContext";
import type { Invoice } from "../../../types/invoice";

export function FundingReceiptSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  const transaction = invoice.fundingTransaction;
  const offeredAmount = invoice.riskPassport?.suggestedAdvanceAmountUsdc;
  const amount = transaction?.amountUsdc ?? offeredAmount;
  const isDevnetDemoTransfer = Boolean(
    transaction
    && transaction.network === "SOLANA_DEVNET"
    && offeredAmount
    && transaction.amountUsdc < offeredAmount,
  );
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
          <h1>{isDevnetDemoTransfer
            ? t("Devnet demo transfer confirmed", "Devnet 데모 전송이 확인되었습니다")
            : t("Your USDC early settlement has been paid", "USDC 조기정산 지급이 완료되었습니다")}</h1>
          <p>{isDevnetDemoTransfer
            ? t(
              "A small USDC transfer verified the connected payout wallet on Solana Devnet.",
              "Solana Devnet에서 소액 USDC 전송으로 연결된 지급 지갑을 검증했습니다.",
            )
            : t(
              "The approved RWA issuance request has been funded on Solana Devnet.",
              "승인된 RWA 발행 요청에 따라 Solana Devnet에서 조기정산 금액이 지급되었습니다.",
            )}</p>
        </div>
        <span className="funding-receipt__chip">
          <CheckCircle size={13} weight="fill" aria-hidden="true" />
          {isDevnetDemoTransfer ? t("DEMO VERIFIED", "데모 확인") : t("USDC PAID", "지급 완료")}
        </span>
      </header>

      <div className="funding-receipt__summary">
        <article className="funding-receipt__amount">
          <span className="funding-receipt__icon">
            <Coins size={24} weight="fill" aria-hidden="true" />
          </span>
          <div>
            <span>{isDevnetDemoTransfer
              ? t("Demo transfer received", "데모 수령액")
              : t("Early settlement received", "조기정산 수령액")}</span>
            <strong>{amount?.toLocaleString() ?? "—"} <small>USDC</small></strong>
            <p>{isDevnetDemoTransfer
              ? t(
                `Demo transfer only · Offer amount ${offeredAmount?.toLocaleString()} USDC`,
                `데모 전송 전용 · 제안 금액 ${offeredAmount?.toLocaleString()} USDC`,
              )
              : t(
                "Available in your connected settlement wallet",
                "연결한 정산 지갑에서 사용할 수 있습니다",
              )}</p>
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
