import { useLanguage } from "../../../i18n/LanguageContext";

export function FundingProgressSection() {
  const { t } = useLanguage();
  return <section><h2>{t("Treasury Agent processing", "Treasury Agent 처리 중")}</h2><p>{t("Processing the AP2 Mandate and investment-policy verification results.", "AP2 Mandate와 투자 정책 검증 결과를 처리하고 있습니다.")}</p></section>;
}
