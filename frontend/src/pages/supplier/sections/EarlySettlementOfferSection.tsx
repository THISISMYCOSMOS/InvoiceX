import { Link } from "react-router-dom";
import { ErrorState } from "../../../components/ErrorState";
import type { Invoice } from "../../../types/invoice";
import { KRW_PER_USDC, PLATFORM_FEE_USDC } from "../../../mocks/demoScenario";
import { useLanguage } from "../../../i18n/LanguageContext";

const krwFormatter = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "KRW",
  maximumFractionDigits: 0,
});
const usdcFormatter = new Intl.NumberFormat("en-US");

function shortenAddress(address: string | undefined): string {
  if (!address) return "-";
  return address.length > 12 ? `${address.slice(0, 4)}...${address.slice(-4)}` : address;
}

export function EarlySettlementOfferSection({
  invoice,
  onAccept,
  onDecline = () => undefined,
  connectedWalletAddress,
  requireConnectedWallet = false,
  isAccepting = false,
  error,
}: {
  invoice: Invoice;
  onAccept: () => void;
  onDecline?: () => void;
  connectedWalletAddress?: string | null;
  requireConnectedWallet?: boolean;
  isAccepting?: boolean;
  error?: unknown;
}) {
  const { t } = useLanguage();
  const passport = invoice.riskPassport;
  const score = passport?.riskScore;
  const advanceRate =
    passport?.suggestedAdvanceRateBps === null || passport?.suggestedAdvanceRateBps === undefined
      ? undefined
      : passport.suggestedAdvanceRateBps / 100;
  const proceeds = passport?.suggestedAdvanceAmountUsdc ?? null;
  const faceValueUsdc = Math.round(invoice.invoiceAmountKrw / KRW_PER_USDC);
  // Everything the supplier gives up: the discount plus the platform fee.
  const totalCost = proceeds === null ? null : faceValueUsdc - proceeds + PLATFORM_FEE_USDC;
  const payoutWalletAddress = connectedWalletAddress ?? invoice.supplier.walletAddress;
  const walletRequired = requireConnectedWallet && !connectedWalletAddress;
  const riskFactors = [
    ...(passport?.positiveFactors ?? []).map((factor) => ({ ...factor, positive: true })),
    ...(passport?.riskFactors ?? []).map((factor) => ({ ...factor, positive: false })),
  ];

  return (
    <section className="early-offer">
      <header className="early-offer__heading">
        <div>
          <p className="detail-breadcrumb">{t("Invoices", "인보이스")} / {invoice.id} / {t("Early settlement offer", "조기정산 제안")}</p>
          <h1>{t("Your early settlement offer is ready", "조기정산 제안이 준비되었습니다")}</h1>
          <p>{t("Review the Risk Passport, expected proceeds, and fees before requesting RWA issuance.", "RWA 발행 요청 전에 Risk Passport, 예상 수령액 및 수수료를 확인하세요.")}</p>
        </div>
        <span className="offer-ready-chip">{t("OFFER READY", "제안 준비 완료")}</span>
      </header>

      <div className="early-offer__grid">
        <section className="risk-score-card">
          <span className="low-risk-chip">{t("LOW RISK", "낮은 위험")}</span>
          <strong>{score ?? "-"}</strong>
          <small>/100</small>
          <h2>{t("Invoice Risk Score", "인보이스 위험 점수")}</h2>
          <p>{t("Buyer verification and payment history support this score.", "구매기업 확인과 결제 이력이 이 점수의 근거입니다.")}</p>
          <dl>
            {riskFactors.map((factor) => (
              <div key={factor.title}>
                <dt>{factor.title}</dt>
                <dd>{factor.positive ? t("Passed", "통과") : t("Review", "검토")}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="offer-proceeds-column">
          <article className="offer-proceeds-card">
            <span className="expected-proceeds-chip">{t("EXPECTED PROCEEDS", "예상 수령액")}</span>
            <h2>{proceeds === null ? "-" : `${usdcFormatter.format(proceeds)} USDC`}</h2>
            <p>{t(
              `Estimated using the hackathon mock rate of ₩${usdcFormatter.format(KRW_PER_USDC)} / USDC.`,
              `해커톤 Mock 환율인 1 USDC당 ₩${usdcFormatter.format(KRW_PER_USDC)}을 적용한 예상치입니다.`,
            )}</p>
            <dl>
              <div><dt>{t("Invoice amount", "인보이스 금액")}</dt><dd>{krwFormatter.format(invoice.invoiceAmountKrw)}</dd></div>
              <div><dt>{t("Advance rate", "선지급률")}</dt><dd>{advanceRate === undefined ? "-" : `${advanceRate}%`}</dd></div>
              <div><dt>{t("Platform fee", "플랫폼 수수료")}</dt><dd>{usdcFormatter.format(PLATFORM_FEE_USDC)} USDC</dd></div>
              <div><dt>{t("Estimated total early settlement cost", "예상 조기정산 총비용")}</dt><dd>{totalCost === null ? "-" : `${usdcFormatter.format(totalCost)} USDC`}</dd></div>
              <div><dt>{t("Payment method", "지급 방식")}</dt><dd>USDC · {shortenAddress(payoutWalletAddress)}</dd></div>
            </dl>
          </article>
          <p className="offer-disclosure">
            {t("Funds are paid after an eligible investor's Treasury Agent purchases the RWA. Matching is not guaranteed.", "적격 투자자의 Treasury Agent가 RWA를 매입한 후 자금이 지급됩니다. 투자 매칭은 보장되지 않습니다.")}
          </p>
          {walletRequired ? (
            <p className="offer-wallet-notice" role="status">
              {t("Connect the supplier payout wallet before accepting the offer.", "제안을 수락하기 전에 공급기업 지급 지갑을 연결하세요.")} {" "}
              <Link to="/supplier/company-wallet">{t("Connect wallet", "지갑 연결")}</Link>
            </p>
          ) : connectedWalletAddress ? (
            <p className="offer-wallet-notice" role="status">
              {t("Connected payout wallet", "연결된 지급 지갑")}: {shortenAddress(connectedWalletAddress)}
            </p>
          ) : null}
          {error !== undefined && error !== null && <ErrorState error={error} />}
          <footer className="offer-actions">
            <button type="button" className="secondary-button" onClick={onDecline}>{t("Decline offer", "제안 거절")}</button>
            <button type="button" className="primary-button" onClick={onAccept} disabled={walletRequired || isAccepting}>
              {isAccepting
                ? t("Submitting...", "처리 중...")
                : t("Accept & request RWA issuance", "수락 및 RWA 발행 요청")}
            </button>
          </footer>
        </section>
      </div>
    </section>
  );
}
