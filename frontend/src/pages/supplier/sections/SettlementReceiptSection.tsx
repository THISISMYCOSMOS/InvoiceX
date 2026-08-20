import { TransactionReceipt } from "../../../components/TransactionReceipt";
import type { Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";
import { formatInvoiceAmount } from "../../../types/invoice";

export function SettlementReceiptSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  return <section><h2>{t("Maturity settlement complete", "만기 정산 완료")}</h2>{invoice.settlement && <dl><dt>{t("RWA face value", "RWA 액면가")}</dt><dd>{formatInvoiceAmount(invoice.settlement.invoiceFaceValueUsdc, "USDC")}</dd><dt>{t("Investor settlement", "투자자 만기 수령액")}</dt><dd>{formatInvoiceAmount(invoice.settlement.investorSettlementUsdc, "USDC")}</dd><dt>{t("Platform fee", "플랫폼 수수료")}</dt><dd>{formatInvoiceAmount(invoice.settlement.platformFeeUsdc, "USDC")}</dd></dl>}{invoice.settlementTransaction && <TransactionReceipt transaction={invoice.settlementTransaction} />}</section>;
}
