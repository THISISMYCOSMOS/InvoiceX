import type { RiskPassport } from "../types/agents";
import { useLanguage } from "../i18n/LanguageContext";

export function RiskPassportSummary({ passport }: { passport: RiskPassport }) {
  const { t } = useLanguage();
  return <section><h2>Risk Passport</h2><p>Risk Score: {passport.riskScore ?? t("Review required", "확인 필요")}</p><p>{t("Suggested advance", "선지급 제안")}: {passport.suggestedAdvanceAmountUsdc ?? "-"} USDC</p><ul>{passport.positiveFactors.map((factor) => <li key={factor.title}>{factor.title}: {factor.description}</li>)}</ul></section>;
}
