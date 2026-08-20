import { CheckCircle, CircleNotch, ShieldCheck, Vault } from "@phosphor-icons/react";
import { useLanguage } from "../../../i18n/LanguageContext";
import { formatInvoiceAmount, type Invoice } from "../../../types/invoice";

function formatDecisionStatus(
  status: NonNullable<Invoice["agentDecision"]>["status"],
  t: (english: string, korean: string) => string,
) {
  const labels: Record<string, [string, string]> = {
    PENDING: ["Awaiting evaluation", "평가 대기"],
    APPROVED: ["Approved", "승인됨"],
    EXECUTED: ["Purchase executed", "매수 실행 완료"],
    REJECTED: ["Not eligible", "매수 조건 미충족"],
    FAILED: ["Execution needs attention", "실행 확인 필요"],
  };
  const label = labels[status] ?? ["Evaluating", "평가 중"];
  return t(...label);
}

export function FundingProgressSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  const decision = invoice.agentDecision;
  const checkEntries = Object.entries(decision?.checks ?? {});
  const amount = decision?.amountUsdc ?? invoice.riskPassport?.suggestedAdvanceAmountUsdc;

  return (
    <section className="funding-progress">
      <header className="funding-progress__heading">
        <div>
          <span>{t("AGENT INVESTMENT", "AGENT 자동 투자")}</span>
          <h1>{t("Treasury Agent is evaluating this issued RWA", "Treasury Agent가 발행된 RWA를 평가하고 있습니다")}</h1>
          <p>{t("Only an active investment mandate and its signed criteria can trigger an automatic purchase.", "활성 자동 투자 권한과 서명한 투자 조건을 모두 충족할 때만 자동 매수를 진행합니다.")}</p>
        </div>
        <span className="funding-progress__status"><CircleNotch size={14} weight="bold" className="funding-progress__spin" aria-hidden="true" /> {t("Processing", "처리 중")}</span>
      </header>

      <div className="funding-progress__grid">
        <article>
          <span className="funding-progress__icon" aria-hidden="true"><CheckCircle size={20} weight="fill" /></span>
          <div>
            <span>{t("RWA issuance", "RWA 발행")}</span>
            <strong>{t("Complete", "완료")}</strong>
            <p>{t("Invoice RWA is ready for an eligible investment review.", "인보이스 RWA가 적격 투자 검토를 위해 준비되었습니다.")}</p>
          </div>
        </article>
        <article>
          <span className="funding-progress__icon funding-progress__icon--violet" aria-hidden="true"><ShieldCheck size={20} weight="fill" /></span>
          <div>
            <span>{t("Mandate evaluation", "Mandate 평가")}</span>
            <strong>{decision ? formatDecisionStatus(decision.status, t) : t("Waiting for an active mandate", "활성 Mandate 대기")}</strong>
            <p>{decision?.reason ?? t("The Agent checks the signed investment policy for this invoice.", "Agent가 이 인보이스에 대해 서명된 투자 조건을 확인합니다.")}</p>
          </div>
        </article>
        <article>
          <span className="funding-progress__icon funding-progress__icon--slate" aria-hidden="true"><Vault size={20} weight="fill" /></span>
          <div>
            <span>{t("Expected purchase", "예상 매수")}</span>
            <strong>{amount === undefined || amount === null ? "—" : formatInvoiceAmount(amount, "USDC")}</strong>
            <p>{t("The supplier receives funds only after the Agent completes an eligible purchase.", "Agent가 적격 매수를 완료한 뒤에만 공급기업에 자금이 지급됩니다.")}</p>
          </div>
        </article>
      </div>

      {checkEntries.length > 0 && (
        <section className="funding-progress__checks" aria-label={t("Agent policy checks", "Agent 정책 확인 항목")}>
          <h2>{t("Policy checks", "정책 확인 항목")}</h2>
          <ul>
            {checkEntries.map(([check, passed]) => (
              <li key={check} className={passed ? "is-passed" : "is-pending"}>
                <CheckCircle size={14} weight={passed ? "fill" : "regular"} aria-hidden="true" />
                <span>{check}</span>
                <strong>{passed ? t("Passed", "통과") : t("Pending", "대기")}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
