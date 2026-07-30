import { RiskPassportSummary } from "../../../components/RiskPassportSummary";
import type { Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

export function EarlySettlementOfferSection({ invoice, onAccept }: { invoice: Invoice; onAccept: () => void }) {
  const { t } = useLanguage();
  return <section>{invoice.riskPassport && <RiskPassportSummary passport={invoice.riskPassport} />}<p>{t("Estimated proceeds", "예상 수령액")}: 18,800 USDC</p><p>{t("Early-settlement fee", "조기정산 비용")}: 1,200 USDC</p><button type="button" onClick={onAccept}>{t("Accept terms and request early settlement", "조건 동의 및 조기정산 신청")}</button></section>;
}
