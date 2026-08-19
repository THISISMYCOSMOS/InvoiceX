import { CheckCircle } from "@phosphor-icons/react";
import { getInvoiceDisplayReference } from "../../../hooks/useInvoices";
import { useLanguage } from "../../../i18n/LanguageContext";
import type { RiskPassport } from "../../../types/agents";
import type { Invoice } from "../../../types/invoice";

export type OfferStage = "risk" | "terms" | "issuance";

type ScoreFactor = RiskPassport["scoreFactors"][number];
type SettlementTerms = NonNullable<RiskPassport["earlySettlementTerms"]>;

const FALLBACK_FACTORS: ScoreFactor[] = [
  { key: "BUYER_CREDIT_QUALITY", label: "Buyer Credit Quality", score: 22, maxScore: 25, source: "SYNTHETIC_DEMO_DATA", detail: "A-equivalent synthetic corporate credit profile", synthetic: true },
  { key: "BUYER_PAYMENT_HISTORY", label: "Buyer Payment History", score: 18, maxScore: 20, source: "SYNTHETIC_DEMO_DATA", detail: "1 late payment across 24 synthetic invoices", synthetic: true },
  { key: "SUPPLIER_BUYER_HISTORY", label: "Supplier–Buyer Transaction History", score: 13, maxScore: 15, source: "SYNTHETIC_DEMO_DATA", detail: "24 synthetic prior transactions", synthetic: true },
  { key: "REMAINING_MATURITY", label: "Remaining Maturity", score: 8, maxScore: 10, source: "INVOICE_DATA", detail: "Invoice due-date calculation", synthetic: false },
  { key: "INVOICE_CONCENTRATION", label: "Invoice Size / Concentration", score: 5, maxScore: 5, source: "INVOICEX_DATA", detail: "Current InvoiceX portfolio exposure", synthetic: false },
  { key: "DOCUMENT_INTEGRITY", label: "Document Integrity & Anomaly", score: 20, maxScore: 25, source: "DOCUMENT_AGENT", detail: "Cross-document consistency confirmed", synthetic: false },
];

function deriveTerms(invoice: Invoice): SettlementTerms | null {
  const passport = invoice.riskPassport;
  if (passport?.earlySettlementTerms) return passport.earlySettlementTerms;
  const faceValue = passport?.invoiceFaceValueUsdc
    ?? ((invoice.currency === "USD" || invoice.currency === "USDC") ? invoice.invoiceAmount : null);
  const advance = passport?.suggestedAdvanceAmountUsdc;
  if (faceValue == null || advance == null) return null;
  const haircut = Math.max(0, faceValue - advance);
  const reserve = Math.floor(haircut / 3);
  const discount = haircut - reserve;
  const investorReturn = Math.floor(discount * 0.7);
  return {
    faceValueUsdc: faceValue,
    discountAmountUsdc: discount,
    discountRateBps: faceValue ? Math.floor((discount * 10_000) / faceValue) : 0,
    investorRequiredReturnUsdc: investorReturn,
    platformFeeUsdc: discount - investorReturn,
    reserveAmountUsdc: reserve,
    reserveRateBps: faceValue ? Math.floor((reserve * 10_000) / faceValue) : 0,
    initialAdvanceUsdc: advance,
    expectedReserveReturnUsdc: reserve,
    expectedFinalProceedsUsdc: advance + reserve,
    settlementAsset: "USDC",
    network: "SOLANA_DEVNET",
  };
}

function formatUsdc(value: number | null | undefined) {
  if (value == null) return "N/A";
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value)} USDC`;
}

function sourceLabel(source: ScoreFactor["source"], t: (en: string, ko: string) => string) {
  const labels = {
    SYNTHETIC_DEMO_DATA: "Synthetic Demo Data",
    INVOICE_DATA: t("Invoice Data", "인보이스 데이터"),
    INVOICEX_DATA: t("InvoiceX Data", "InvoiceX 데이터"),
    DOCUMENT_AGENT: "Document Agent",
  } as const;
  return labels[source];
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
  const factors = passport?.scoreFactors?.length
    ? passport.scoreFactors
    : score === 86
      ? FALLBACK_FACTORS
      : [];
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
            <p>{t("Synthetic fields are explicitly labelled and are never generated by Gemini.", "Synthetic 항목은 명확히 표시되며 Gemini가 임의 생성하지 않습니다.")}</p>
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
                    <span className={factor.synthetic ? "is-synthetic" : ""}>{sourceLabel(factor.source, t)}</span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>

        <footer className="offer-stage-actions is-split">
          <button type="button" className="secondary-button" onClick={onRequestRiskReview} disabled={isRequestingRiskReview}>
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
            <p>{t("Understand what you receive today, what you pay, and what is temporarily reserved.", "오늘 받는 금액, 부담하는 비용, 일시 유보되는 금액을 구분해 확인하세요.")}</p>
          </div>
          <span className="offer-ready-chip">{t("PRICING READY", "조건 산정 완료")}</span>
        </header>

        {terms ? (
          <>
            <div className="settlement-summary-grid">
              <article><span>Invoice Face Value</span><strong>{formatUsdc(terms.faceValueUsdc)}</strong></article>
              <article className="is-primary"><span>{t("Initial Advance", "오늘 수령 예정")}</span><strong>{formatUsdc(terms.initialAdvanceUsdc)}</strong></article>
              <article><span>{t("Expected Final Proceeds", "정상 정산 시 최종 예상 수령")}</span><strong>{formatUsdc(terms.expectedFinalProceedsUsdc)}</strong></article>
            </div>

            <div className="settlement-terms-layout">
              <section className="settlement-breakdown-card">
                <header><h2>{t("Economics breakdown", "조기정산 금액 구성")}</h2><span>{t("MVP policy", "MVP 정책")}</span></header>
                <dl>
                  <div><dt>Invoice Face Value</dt><dd>{formatUsdc(terms.faceValueUsdc)}</dd></div>
                  <div className="is-cost"><dt>{t("Discount", "Discount · 금융비용")}</dt><dd>- {formatUsdc(terms.discountAmountUsdc)}</dd></div>
                  <div className="is-sub"><dt>Investor Required Return</dt><dd>{formatUsdc(terms.investorRequiredReturnUsdc)}</dd></div>
                  <div className="is-sub"><dt>InvoiceX Transaction Fee</dt><dd>{formatUsdc(terms.platformFeeUsdc)}</dd></div>
                  <div className="is-reserve"><dt>{t("Reserve", "Reserve · 일시 유보금")}</dt><dd>- {formatUsdc(terms.reserveAmountUsdc)}</dd></div>
                  <div className="is-total"><dt>{t("Initial Advance", "오늘 수령 예정")}</dt><dd>{formatUsdc(terms.initialAdvanceUsdc)}</dd></div>
                  <div className="is-return"><dt>{t("Expected Reserve Return", "정상 만기 시 예상 Reserve 반환")}</dt><dd>+ {formatUsdc(terms.expectedReserveReturnUsdc)}</dd></div>
                  <div className="is-final"><dt>{t("Expected Final Proceeds", "정상 정산 시 최종 예상 수령")}</dt><dd>{formatUsdc(terms.expectedFinalProceedsUsdc)}</dd></div>
                </dl>
              </section>

              <aside className="settlement-explanation-column">
                <section className="reserve-explanation-card">
                  <span>Reserve ≠ Fee</span>
                  <h2>{t("What is the Reserve?", "Reserve란?")}</h2>
                  <p>{t("A temporary holdback for reductions, disputes, or settlement differences at maturity. Any unused amount is returned to the supplier after normal settlement.", "만기 정산 과정의 감액, 분쟁 또는 정산 차이를 처리하기 위한 일시 유보금입니다. 정상 정산 후 사용되지 않은 금액은 공급기업에 반환됩니다.")}</p>
                </section>
                <section className="settlement-metadata-card">
                  <div><span>Discount Rate</span><strong>{terms.discountRateBps / 100}%</strong></div>
                  <div><span>Reserve Rate</span><strong>{terms.reserveRateBps / 100}%</strong></div>
                  <div><span>{t("Due date", "만기일")}</span><strong>{invoice.dueDate}</strong></div>
                  <div><span>{t("Settlement asset", "정산 자산")}</span><strong>{terms.settlementAsset}</strong></div>
                  <div><span>{t("Network", "네트워크")}</span><strong>Solana Devnet</strong></div>
                </section>
              </aside>
            </div>
          </>
        ) : <p className="offer-data-unavailable">{t("Early-settlement terms are unavailable. Please retry the risk assessment.", "조기정산 조건을 불러올 수 없습니다. Risk 산정을 다시 시도해 주세요.")}</p>}

        <p className="offer-disclosure">{t("Funds are paid after an eligible investor's Treasury Agent purchases the RWA. Matching is not guaranteed.", "적격 투자자의 Treasury Agent가 RWA를 매입한 후 자금이 지급됩니다. 투자 매칭은 보장되지 않습니다.")}</p>
        <footer className="offer-stage-actions is-split">
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
          <div><dt>Initial Advance</dt><dd>{formatUsdc(terms?.initialAdvanceUsdc)}</dd></div>
          <div><dt>Reserve</dt><dd>{formatUsdc(terms?.reserveAmountUsdc)}</dd></div>
        </dl>
        <p><CheckCircle weight="fill" aria-hidden="true" />{t("The supplier agreed to the disclosed discount, reserve, and settlement terms.", "공급기업이 안내된 Discount, Reserve 및 정산 조건에 동의했습니다.")}</p>
      </section>

      <footer className="offer-stage-actions is-split">
        <button type="button" className="secondary-button" onClick={() => onStageChange("terms")} disabled={isRequesting}>{t("Back", "이전")}</button>
        <button type="button" className="primary-button" onClick={onAccept} disabled={isRequesting || !terms}>{isRequesting ? t("Requesting RWA issuance…", "RWA 발행 요청 중…") : t("Request RWA issuance", "RWA 발행 요청")}</button>
      </footer>
      {requestError && <p className="offer-request-error" role="alert">{requestError}</p>}
    </section>
  );
}
