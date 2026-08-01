import { CheckCircle, Clock, Coins } from "@phosphor-icons/react";
import type { Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

export function RwaIssuedSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  const amount = invoice.riskPassport?.suggestedAdvanceAmountUsdc;

  return (
    <section className="rwa-issued">
      <p className="detail-breadcrumb">{t("Invoices", "인보이스")} / {invoice.id} / {t("RWA issued", "RWA 발행 완료")}</p>
      <article className="rwa-issued-card">
        <header>
          <span className="rwa-issued-card__icon" aria-hidden="true"><CheckCircle size={25} weight="fill" /></span>
          <div>
            <span className="rwa-issued-card__eyebrow">{t("AUTOMATED INVESTMENT", "자동 투자 실행")}</span>
            <h1>{t("Treasury Agent is processing the RWA investment", "Treasury Agent가 RWA 자동 투자를 처리하고 있습니다")}</h1>
            <p>{t(
              "The institution's AP2 Mandate and investment policy are being evaluated before USDC is paid to your settlement wallet.",
              "기관의 AP2 Mandate와 자체 투자 정책을 검증한 뒤 정산 지갑으로 USDC가 자동 지급됩니다.",
            )}</p>
          </div>
          <span className="rwa-issued-card__badge"><Clock size={13} weight="fill" aria-hidden="true" /> {t("AGENT PROCESSING", "AGENT 처리 중")}</span>
        </header>
        <div className="rwa-issued-card__body">
          <dl>
            <div><dt>{t("RWA asset", "RWA 자산")}</dt><dd>RWA-{invoice.id}</dd></div>
            <div><dt>{t("Target purchase", "투자 예정 금액")}</dt><dd>{amount?.toLocaleString() ?? "—"} USDC</dd></div>
            <div><dt>{t("Mandate owner", "Mandate 기관")}</dt><dd>{invoice.investor.name}</dd></div>
          </dl>
          <div className="rwa-issued-card__notice">
            <span><Coins size={18} weight="fill" aria-hidden="true" /></span>
            <p>{t("Treasury Agent automatically executes the approved investment and USDC transfer.", "Treasury Agent가 승인된 투자를 자동 실행하고 정산 지갑으로 USDC를 지급합니다.")}</p>
          </div>
        </div>
        <ol className="rwa-issued-card__steps" aria-label={t("Early settlement progress", "조기정산 진행 상황")}>
          <li className="is-complete">{t("RWA issued", "RWA 발행 완료")}</li>
          <li className="is-current">{t("Automated Agent investment", "Agent 자동 투자")}</li>
          <li>{t("USDC paid", "USDC 지급")}</li>
        </ol>
      </article>
    </section>
  );
}
