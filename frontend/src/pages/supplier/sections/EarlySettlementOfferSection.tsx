import type { Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

export function EarlySettlementOfferSection({
  invoice,
  onAccept,
}: {
  invoice: Invoice;
  onAccept: () => void;
}) {
  const { t } = useLanguage();
  const score = invoice.riskPassport?.riskScore ?? 86;
  const advanceRate = (invoice.riskPassport?.suggestedAdvanceRateBps ?? 9_400) / 100;

  return (
    <section className="early-offer">
      <header className="early-offer__heading">
        <div>
          <p className="detail-breadcrumb">{t("Invoice", "인보이스")} / {invoice.id}</p>
          <h1>{t("Your RWA issuance preparation is complete", "RWA 발행 준비가 완료되었습니다")}</h1>
          <p>{t("Before requesting RWA issuance, review the Risk Passport, expected proceeds, and fees.", "RWA 발행 요청 전에 Risk Passport, 예상 수령액 및 수수료를 확인하세요.")}</p>
        </div>
        <span className="offer-ready-chip">{t("OFFER READY", "제안 준비 완료")}</span>
      </header>

      <div className="early-offer__grid">
        <section className="risk-score-card">
          <span className="low-risk-chip">{t("LOW RISK", "낮은 위험")}</span>
          <h2>Risk Passport</h2>
          <strong>{score}</strong>
          <small>/100</small>
          <p>{t("A risk assessment based on buyer verification and payment history.", "구매기업 확인과 결제 이력에 기반한 인보이스 위험 평가입니다.")}</p>
          <dl>
            <div><dt>{t("Buyer verified", "구매기업 확인")}</dt><dd>{t("Passed", "통과")}</dd></div>
            <div><dt>{t("Company KYB", "기업 KYB")}</dt><dd>{t("Passed", "통과")}</dd></div>
            <div><dt>{t("Duplicate signal", "중복 신호")}</dt><dd>{t("None", "없음")}</dd></div>
            <div><dt>{t("Prior late payments", "과거 연체 결제")}</dt><dd>{t("1 of 24", "24건 중 1건")}</dd></div>
          </dl>
        </section>

        <section className="offer-proceeds-column">
          <article className="offer-proceeds-card">
            <span className="expected-proceeds-chip">{t("EXPECTED PROCEEDS", "예상 수령액")}</span>
            <h2>18,800 USDC</h2>
            <p>{t("Estimated at ₩1,000 per USDC.", "1 USDC당 ₩1,000을 적용한 예상치입니다.")}</p>
            <dl>
              <div><dt>{t("Invoice amount", "인보이스 금액")}</dt><dd>₩20,000,000</dd></div>
              <div><dt>{t("Advance rate", "선지급률")}</dt><dd>{advanceRate}%</dd></div>
              <div><dt>{t("Platform fee", "플랫폼 수수료")}</dt><dd>200 USDC</dd></div>
              <div><dt>{t("Estimated total early settlement cost", "예상 조기정산 총비용")}</dt><dd>1,200 USDC</dd></div>
              <div><dt>{t("Payment method", "지급 방식")}</dt><dd>USDC · 8xK2...p91Q</dd></div>
            </dl>
          </article>
          <p className="offer-disclosure">
            {t("Funds are paid after an eligible investor's Treasury Agent purchases the RWA. Matching is not guaranteed.", "적격 투자자의 Treasury Agent가 RWA를 매입한 후 자금이 지급됩니다. 투자 매칭은 보장되지 않습니다.")}
          </p>
          <footer className="offer-actions">
            <button type="button" className="primary-button" onClick={onAccept}>{t("Request RWA issuance", "RWA 발행 요청")}</button>
          </footer>
        </section>
      </div>
    </section>
  );
}
