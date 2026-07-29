import type { RiskPassport } from "../types/agents";

export function RiskPassportSummary({ passport }: { passport: RiskPassport }) {
  return <section><h2>Risk Passport</h2><p>Risk Score: {passport.riskScore ?? "확인 필요"}</p><p>선지급 제안: {passport.suggestedAdvanceAmountUsdc ?? "-"} USDC</p><ul>{passport.positiveFactors.map((factor) => <li key={factor.title}>{factor.title}: {factor.description}</li>)}</ul></section>;
}
