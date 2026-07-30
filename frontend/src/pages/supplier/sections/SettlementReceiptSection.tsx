import { TransactionReceipt } from "../../../components/TransactionReceipt";
import type { Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

export function SettlementReceiptSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  return <section><h2>{t("Maturity settlement complete", "만기 정산 완료")}</h2>{invoice.settlement && <dl><dt>{t("Investor proceeds", "투자기관 수령")}</dt><dd>{invoice.settlement.investorSettlementUsdc} USDC</dd><dt>{t("Platform fee", "플랫폼 수수료")}</dt><dd>{invoice.settlement.platformFeeUsdc} USDC</dd></dl>}{invoice.settlementTransaction && <TransactionReceipt transaction={invoice.settlementTransaction} />}</section>;
}
