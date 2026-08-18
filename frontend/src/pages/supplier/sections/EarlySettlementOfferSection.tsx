import { formatInvoiceAmount, type Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

export function EarlySettlementOfferSection({
  invoice,
  onAccept,
  isRequesting = false,
  requestError,
}: {
  invoice: Invoice;
  onAccept: () => void;
  isRequesting?: boolean;
  requestError?: string;
}) {
  const { t } = useLanguage();
  const score = invoice.riskPassport?.riskScore ?? 86;
  const advanceRate = (invoice.riskPassport?.suggestedAdvanceRateBps ?? 9_400) / 100;
  const expectedProceeds = invoice.riskPassport?.suggestedAdvanceAmountUsdc ?? 1;
  // Small Devnet invoices are rounded to whole USDC. Derive the cost from the
  // policy rate so a rounded payout does not misleadingly show a zero fee.
  const estimatedCost = advanceRate > 0
    ? expectedProceeds * ((100 - advanceRate) / advanceRate)
    : 0;
  const formatUsdc = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
    minimumFractionDigits: estimatedCost > 0 && estimatedCost < 1 ? 2 : 0,
  }).format(estimatedCost);

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
            <h2>{expectedProceeds.toLocaleString()} USDC</h2>
            <p>{t("The invoice and expected proceeds are denominated in USDC.", "인보이스와 예상 수령액은 USDC 기준입니다.")}</p>
            <dl>
              <div><dt>{t("Invoice amount", "인보이스 금액")}</dt><dd>{formatInvoiceAmount(invoice.invoiceAmount, invoice.currency)}</dd></div>
              <div><dt>{t("Advance rate", "선지급률")}</dt><dd>{advanceRate}%</dd></div>
              <div><dt>{t("Estimated total early settlement cost", "예상 조기정산 총비용")}</dt><dd>{formatUsdc} USDC</dd></div>
              <div><dt>{t("Payment method", "지급 방식")}</dt><dd>Circle USDC · Solana Devnet</dd></div>
            </dl>
          </article>
          <p className="offer-disclosure">
            {t("Funds are paid after an eligible investor's Treasury Agent purchases the RWA. Matching is not guaranteed.", "적격 투자자의 Treasury Agent가 RWA를 매입한 후 자금이 지급됩니다. 투자 매칭은 보장되지 않습니다.")}
          </p>
          <footer className="offer-actions">
            <button type="button" className="primary-button" onClick={onAccept} disabled={isRequesting}>
              {isRequesting
                ? t("Requesting RWA issuance…", "RWA 발행 요청 중...")
                : t("Request RWA issuance", "RWA 발행 요청")}
            </button>
          </footer>
          {requestError && <p className="offer-request-error" role="alert">{requestError}</p>}
        </section>
      </div>
    </section>
  );
}
