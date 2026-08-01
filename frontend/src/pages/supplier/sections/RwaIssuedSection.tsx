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
            <span className="rwa-issued-card__eyebrow">{t("RWA ISSUANCE COMPLETE", "RWA 발행 완료")}</span>
            <h1>{t("Your RWA is ready for investor purchase", "RWA 발행이 완료되어 투자자 매수를 기다리고 있습니다")}</h1>
            <p>{t(
              "USDC is paid to your settlement wallet only after an investor purchases this RWA.",
              "투자자가 이 RWA를 매수한 뒤에만 조기정산 USDC가 정산 지갑으로 지급됩니다.",
            )}</p>
          </div>
          <span className="rwa-issued-card__badge"><Clock size={13} weight="fill" aria-hidden="true" /> {t("AWAITING INVESTMENT", "투자 대기")}</span>
        </header>
        <div className="rwa-issued-card__body">
          <dl>
            <div><dt>{t("RWA asset", "RWA 자산")}</dt><dd>RWA-{invoice.id}</dd></div>
            <div><dt>{t("Target purchase", "투자 예정 금액")}</dt><dd>{amount?.toLocaleString() ?? "—"} USDC</dd></div>
            <div><dt>{t("Eligible investor", "매수 대상 투자자")}</dt><dd>{invoice.investor.name}</dd></div>
          </dl>
          <div className="rwa-issued-card__notice">
            <span><Coins size={18} weight="fill" aria-hidden="true" /></span>
            <p>{t("Investor purchase triggers the USDC transfer to your connected wallet.", "투자기관의 RWA 매수가 완료되면 연결한 지갑으로 USDC가 지급됩니다.")}</p>
          </div>
        </div>
        <ol className="rwa-issued-card__steps" aria-label={t("Early settlement progress", "조기정산 진행 상황")}>
          <li className="is-complete">{t("RWA issued", "RWA 발행 완료")}</li>
          <li className="is-current">{t("Investor purchase", "투자자 RWA 매수")}</li>
          <li>{t("USDC paid", "USDC 지급")}</li>
        </ol>
      </article>
    </section>
  );
}
