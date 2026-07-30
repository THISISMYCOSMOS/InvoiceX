import { TransactionReceipt } from "../../../components/TransactionReceipt";
import type { Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

export function FundingReceiptSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  return <section><h2>{t("USDC funding complete", "USDC 지급 완료")}</h2>{invoice.fundingTransaction && <TransactionReceipt transaction={invoice.fundingTransaction} />}</section>;
}
