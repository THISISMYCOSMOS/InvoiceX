import { CheckCircle } from "@phosphor-icons/react";
import { getInvoiceDisplayReference } from "../../../hooks/useInvoices";
import { useLanguage } from "../../../i18n/LanguageContext";
import type { RiskPassport } from "../../../types/agents";
import type { Invoice } from "../../../types/invoice";

export type OfferStage = "risk" | "terms" | "issuance";

type SettlementTerms = NonNullable<RiskPassport["earlySettlementTerms"]>;
type CompleteSettlementTerms = SettlementTerms & {
  remainingTermDays: number;
  sofrRateBps: number;
  sofrAsOf: string;
  sofrSource: string;
  buyerRiskScore: number;
  riskSpreadBps: number;
  countryLegalSpreadBps: number;
  annualExpectedYieldBps: number;
  platformFeeShareBps: number;
  expectedInvestorReturnUsdc: number;
  investorSettlementUsdc: number;
  purchaseAmountUsdc: number;
  supplierExpectedSettlementUsdc: number;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function deriveTerms(invoice: Invoice): CompleteSettlementTerms | null {
  const terms = invoice.riskPassport?.earlySettlementTerms;
  if (!terms) return null;
  const requiredValues = [
    terms.faceValueUsdc,
    terms.platformFeeUsdc,
    terms.remainingTermDays,
    terms.sofrRateBps,
    terms.buyerRiskScore,
    terms.riskSpreadBps,
    terms.countryLegalSpreadBps,
    terms.annualExpectedYieldBps,
    terms.platformFeeShareBps,
    terms.expectedInvestorReturnUsdc,
    terms.investorSettlementUsdc,
    terms.purchaseAmountUsdc,
    terms.supplierExpectedSettlementUsdc,
  ];
  return requiredValues.every(isFiniteNumber)
    && typeof terms.sofrAsOf === "string"
    && terms.sofrAsOf.trim().length > 0
    && typeof terms.sofrSource === "string"
    && terms.sofrSource.trim().length > 0
    ? terms as CompleteSettlementTerms
    : null;
}

function formatUsdc(value: number | null | undefined) {
  if (!isFiniteNumber(value)) return "N/A";
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 6 }).format(value)} USDC`;
}

function formatRateBps(value: number | null | undefined) {
  if (!isFiniteNumber(value)) return "N/A";
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value / 100)}%`;
}

export function EarlySettlementOfferSection({
  invoice,
  stage,
  onStageChange,
  onAccept,
  isRequesting = false,
  requestError,
  onRequestRiskReview = () => undefined,
  isRequestingRiskReview = false,
  riskReviewError,
}: {
  invoice: Invoice;
  stage: OfferStage;
  onStageChange: (stage: OfferStage) => void;
  onAccept: () => void;
  isRequesting?: boolean;
  requestError?: string;
  onRequestRiskReview?: () => void;
  isRequestingRiskReview?: boolean;
  riskReviewError?: string;
}) {
  const { t } = useLanguage();
  const passport = invoice.riskPassport;
  const score = passport?.riskScore;
  const coverage = (passport?.dataCoverageBps ?? (score === 86 ? 10_000 : 0)) / 100;
  const factors = passport?.scoreFactors ?? [];
  const terms = deriveTerms(invoice);

  if (stage === "risk") {
    return (
      <section className="risk-passport-stage offer-flow-stage">
        <header className="offer-stage-heading">
          <div>
            <p className="detail-breadcrumb">{t("Invoice", "인보이스")} / {invoice.id}</p>
            <h1>{t("Risk Passport assessment", "Risk Passport 산정 결과")}</h1>
            <p>{t("See how the Risk Agent evaluated this invoice and where each input came from.", "Risk Agent가 이 인보이스를 어떻게 평가했는지와 각 데이터의 출처를 확인하세요.")}</p>
          </div>
          <span className="offer-ready-chip">{t("ASSESSMENT COMPLETE", "산정 완료")}</span>
        </header>

        <div className="risk-passport-stage__layout">
          <section className="risk-passport-score-card">
            <span>{t("Provisional Risk Score", "Provisional Risk Score")}</span>
            <strong>{score ?? "N/A"}</strong>
            <small>/ 100</small>
            <b>{score != null && score >= 80 ? t("Low risk", "낮은 위험") : t("Review required", "확인 필요")}</b>
            <div className="risk-coverage-meter">
              <div><span>Data Coverage</span><strong>{coverage}%</strong></div>
              <i><b style={{ width: `${coverage}%` }} /></i>
            </div>
            <p>{t("Coverage reflects the data available for this Risk Passport.", "이 Risk Passport 산정에 사용된 데이터 범위입니다.")}</p>
          </section>

          <section className="risk-factor-card">
            <header>
              <div><h2>{t("Risk Agent analysis", "Risk Agent 분석 항목")}</h2><p>{t("Completed checks and score contribution", "완료된 검토와 점수 반영 내역")}</p></div>
              <span>{factors.length}/{factors.length}</span>
            </header>
            <div className="risk-factor-list">
              {factors.length === 0 ? (
                <p className="offer-data-unavailable">{t("Factor-level data is not available for this passport.", "이 Risk Passport에는 항목별 데이터가 없습니다.")}</p>
              ) : factors.map((factor) => (
                <article key={factor.key}>
                  <CheckCircle className="risk-factor-check" weight="fill" aria-hidden="true" />
                  <div><h3>{factor.label}</h3><p>{factor.detail ?? t("No detail available", "세부 정보 없음")}</p></div>
                  <div className="risk-factor-result">
                    <strong>{factor.score == null ? "N/A" : `${factor.score} / ${factor.maxScore}`}</strong>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>

        {passport?.hardGate && (
          <section className={`hard-gate-card ${passport.hardGate.passed ? "is-passed" : "is-failed"}`}>
            <header>
              <div><h2>Hard Gate</h2><p>{t("Eligibility checks completed before scoring", "Risk Score 산정 전 필수 적격성 검토")}</p></div>
              <strong>{passport.hardGate.passed ? t("PASSED", "통과") : t("FAILED", "진행 불가")}</strong>
            </header>
            <div>
              {passport.hardGate.checks.map((check) => (
                <article key={check.key} className={check.passed ? "is-passed" : "is-failed"}>
                  <CheckCircle weight="fill" aria-hidden="true" />
                  <span>{check.label}</span>
                  <b>{check.passed ? t("Pass", "통과") : check.reason ?? t("Failed", "실패")}</b>
                </article>
              ))}
            </div>
          </section>
        )}

        <footer className="offer-stage-actions risk-passport-actions">
          <button type="button" className="risk-review-button" onClick={onRequestRiskReview} disabled={isRequestingRiskReview}>
            {isRequestingRiskReview ? t("Submitting review request…", "이의 신청 접수 중…") : t("Request Risk Score review", "Risk Score 이의 신청")}
          </button>
          <button type="button" className="primary-button" onClick={() => onStageChange("terms")}>{t("Review early-settlement terms", "조기정산 조건 확인")}</button>
        </footer>
        {riskReviewError && <p className="offer-request-error" role="alert">{riskReviewError}</p>}
      </section>
    );
  }

  if (stage === "terms") {
    return (
      <section className="settlement-terms-stage offer-flow-stage">
        <header className="offer-stage-heading">
          <div>
            <p className="detail-breadcrumb">{t("Invoice", "인보이스")} / {invoice.id}</p>
            <h1>{t("Review early-settlement terms", "조기정산 조건 확인")}</h1>
            <p>{t("Review the SOFR-based annual yield, investor return, fees, and supplier settlement amount.", "SOFR 기반 연 수익률, 투자자 수익, 수수료와 공급기업 정산액을 확인하세요.")}</p>
          </div>
          <span className="offer-ready-chip">
            {terms ? t("PRICING READY", "조건 산정 완료") : t("CALCULATION FAILED", "조건 계산 불가")}
          </span>
        </header>

        {terms ? (
          <>
            <div className="settlement-summary-grid">
              <article><span>Invoice Face Value</span><strong>{formatUsdc(terms.faceValueUsdc)}</strong></article>
              <article className="is-primary"><span>{t("RWA purchase amount", "RWA 매입가")}</span><strong>{formatUsdc(terms.purchaseAmountUsdc)}</strong></article>
              <article><span>{t("Supplier settlement", "공급기업 정산 예정액")}</span><strong>{formatUsdc(terms.supplierExpectedSettlementUsdc)}</strong></article>
            </div>

            <div className="settlement-terms-layout">
              <section className="settlement-breakdown-card">
                <header><h2>{t("Economics breakdown", "조기정산 금액 구성")}</h2></header>
                <dl>
                  <div><dt>Invoice Face Value</dt><dd>{formatUsdc(terms.faceValueUsdc)}</dd></div>
                  <div><dt>{t("Remaining term", "잔존 만기")}</dt><dd>{terms.remainingTermDays} {t("days", "일")}</dd></div>
                  <div><dt>SOFR <small>({terms.sofrSource}, {terms.sofrAsOf})</small></dt><dd>{formatRateBps(terms.sofrRateBps)}</dd></div>
                  <div><dt>{t("Buyer risk spread", "Buyer Risk Spread")}</dt><dd>+ {formatRateBps(terms.riskSpreadBps)}</dd></div>
                  <div><dt>{t("KR-US country / legal spread", "KR-US Country / Legal Spread")}</dt><dd>+ {formatRateBps(terms.countryLegalSpreadBps)}</dd></div>
                  <div className="is-total"><dt>{t("Investor net annual yield", "투자자 순 연환산 수익률")}</dt><dd>{formatRateBps(terms.annualExpectedYieldBps)}</dd></div>
                  <div><dt>{t("Investor net return", "투자자 순수익")}</dt><dd>{formatUsdc(terms.expectedInvestorReturnUsdc)}</dd></div>
                  <div><dt>{t("Investor settlement", "투자자 만기 수령액")}</dt><dd>{formatUsdc(terms.investorSettlementUsdc)}</dd></div>
                  <div><dt>{t("RWA purchase amount", "RWA 매입가")}</dt><dd>{formatUsdc(terms.purchaseAmountUsdc)}</dd></div>
                  <div><dt>InvoiceX Platform Fee ({formatRateBps(terms.platformFeeShareBps)})</dt><dd>{formatUsdc(terms.platformFeeUsdc)}</dd></div>
                  <div className="is-final"><dt>{t("Supplier settlement", "공급기업 정산 예정액")}</dt><dd>{formatUsdc(terms.supplierExpectedSettlementUsdc)}</dd></div>
                </dl>
              </section>

              <aside className="settlement-explanation-column">
                <section className="reserve-explanation-card">
                  <span>Dynamic Pricing</span>
                  <h2>{t("How is the price calculated?", "가격은 어떻게 산정되나요?")}</h2>
                  <p>{t("Investor net annual yield is SOFR plus the Buyer Risk Spread and the fixed KR-US pilot spread. The purchase amount uses the disclosed closed-form formula; the supplier receives that full amount.", "투자자 순 연환산 수익률은 SOFR, Buyer Risk Spread, 고정 KR-US Pilot Spread의 합입니다. 매입가는 공개된 폐쇄형 공식으로 계산되며 공급기업은 매입가 전액을 수령합니다.")}</p>
                </section>
                <section className="settlement-metadata-card">
                  <div><span>{t("Investor net annual yield", "투자자 순 연환산 수익률")}</span><strong>{formatRateBps(terms.annualExpectedYieldBps)}</strong></div>
                  <div><span>{t("Buyer Risk Score", "Buyer Risk Score")}</span><strong>{terms.buyerRiskScore}</strong></div>
                  <div><span>{t("Due date", "만기일")}</span><strong>{invoice.dueDate}</strong></div>
                  <div><span>{t("Settlement asset", "정산 자산")}</span><strong>{terms.settlementAsset}</strong></div>
                  <div><span>{t("Network", "네트워크")}</span><strong>Solana Devnet</strong></div>
                </section>
              </aside>
            </div>
          </>
        ) : <p className="offer-data-unavailable">{t("Required Dynamic Pricing inputs are missing from the backend response.", "백엔드 응답에 Dynamic Pricing 필수 입력값이 없어 조건을 계산할 수 없습니다.")}</p>}

        <p className="offer-disclosure">{t("Funds are paid after an eligible investor's Treasury Agent purchases the RWA. Matching is not guaranteed.", "적격 투자자의 Treasury Agent가 RWA를 매입한 후 자금이 지급됩니다. 투자 매칭은 보장되지 않습니다.")}</p>
        <footer className="offer-stage-actions offer-stage-actions--paired">
          <button type="button" className="secondary-button" onClick={() => onStageChange("risk")}>{t("Back", "이전")}</button>
          <button type="button" className="primary-button" onClick={() => onStageChange("issuance")} disabled={!terms}>{t("Agree to early-settlement terms", "조기정산 조건 동의")}</button>
        </footer>
      </section>
    );
  }

  return (
    <section className="rwa-issuance-stage offer-flow-stage">
      <header className="offer-stage-heading">
        <div>
          <p className="detail-breadcrumb">{t("Invoice", "인보이스")} / {invoice.id}</p>
          <h1>{t("Review RWA issuance", "RWA 발행 정보 확인")}</h1>
          <p>{t("Confirm the final Invoice Asset information before requesting issuance.", "발행 요청 전 최종 Invoice Asset 정보를 확인하세요.")}</p>
        </div>
        <span className="offer-ready-chip">{t("TERMS AGREED", "조건 동의 완료")}</span>
      </header>

      <section className="issuance-review-card">
        <header><div><span>Invoice Asset</span><h2>{getInvoiceDisplayReference(invoice)}</h2></div><b>{t("READY TO ISSUE", "발행 준비 완료")}</b></header>
        <dl>
          <div><dt>{t("Original Invoice Number", "원본 Invoice Number")}</dt><dd>{getInvoiceDisplayReference(invoice)}</dd></div>
          <div><dt>InvoiceX ID</dt><dd>{invoice.id}</dd></div>
          <div><dt>{t("Buyer", "구매기업")}</dt><dd>{invoice.buyer.name}</dd></div>
          <div><dt>Face Value</dt><dd>{formatUsdc(terms?.faceValueUsdc)}</dd></div>
          <div><dt>{t("Due Date", "만기일")}</dt><dd>{invoice.dueDate}</dd></div>
          <div><dt>Risk Score</dt><dd>{score ?? "N/A"} / 100</dd></div>
          <div><dt>{t("RWA purchase amount", "RWA 매입가")}</dt><dd>{formatUsdc(terms?.purchaseAmountUsdc)}</dd></div>
          <div><dt>{t("Supplier settlement", "공급기업 정산 예정액")}</dt><dd>{formatUsdc(terms?.supplierExpectedSettlementUsdc)}</dd></div>
        </dl>
        <p><CheckCircle weight="fill" aria-hidden="true" />{t("The supplier agreed to the disclosed dynamic pricing and settlement terms.", "공급기업이 안내된 동적 가격 및 정산 조건에 동의했습니다.")}</p>
      </section>

      <footer className="offer-stage-actions offer-stage-actions--paired">
        <button type="button" className="secondary-button" onClick={() => onStageChange("terms")} disabled={isRequesting}>{t("Back", "이전")}</button>
        <button type="button" className="primary-button" onClick={onAccept} disabled={isRequesting || !terms}>{isRequesting ? t("Requesting RWA issuance…", "RWA 발행 요청 중…") : t("Request RWA issuance", "RWA 발행 요청")}</button>
      </footer>
      {requestError && <p className="offer-request-error" role="alert">{requestError}</p>}
    </section>
  );
}
