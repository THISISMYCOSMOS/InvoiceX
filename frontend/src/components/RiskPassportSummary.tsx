import type { RiskPassport } from "../types/agents";
import { useLanguage } from "../i18n/LanguageContext";

export function RiskPassportSummary({ passport }: { passport: RiskPassport }) {
  const { t } = useLanguage();
  return <section><h2>Risk Passport</h2><p>{t("Risk Score", "위험 점수")}: {passport.riskScore ?? t("Review required", "확인 필요")}</p><p>{t("RWA face value", "RWA 기준 채권가치")}: {passport.invoiceFaceValueUsdc ?? "-"} USDC</p><p>{t("Suggested advance", "선지급 제안")}: {passport.suggestedAdvanceAmountUsdc ?? "-"} USDC</p><ul>{passport.positiveFactors.map((factor) => <li key={factor.title}>{factor.title}: {factor.description}</li>)}</ul></section>;
}
