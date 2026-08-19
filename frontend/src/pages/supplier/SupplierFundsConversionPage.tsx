import { ArrowsLeftRight, Bank, CheckCircle, Coins, Info, X } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import { useLanguage } from "../../i18n/LanguageContext";

type ConversionMode = "buy" | "withdraw";
type FiatCurrency = "KRW" | "USD" | "JPY";

const demoRates: Record<FiatCurrency, number> = { KRW: 1404.75, USD: 1, JPY: 149.65 };

function formatAmount(value: number, maximumFractionDigits = 2) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits }).format(value);
}

function parseAmount(value: string) {
  const amount = Number(value.replace(/,/g, ""));
  return Number.isFinite(amount) && amount > 0 ? amount : 0;
}

function QuoteSummary({
  amountLabel,
  amount,
  rate,
  fee,
}: {
  amountLabel: string;
  amount: string;
  rate: string;
  fee: string;
}) {
  return (
    <dl className="funds-conversion-quote">
      <div><dt>{amountLabel}</dt><dd>{amount}</dd></div>
      <div><dt>예상 환율</dt><dd>{rate}</dd></div>
      <div><dt>예상 수수료</dt><dd>{fee}</dd></div>
    </dl>
  );
}

export function SupplierFundsConversionPage({ variant = "supplier" }: { variant?: "supplier" | "investor" }) {
  const { t } = useLanguage();
  const [mode, setMode] = useState<ConversionMode>("buy");
  const [buyCurrency, setBuyCurrency] = useState<FiatCurrency>("KRW");
  const [withdrawCurrency, setWithdrawCurrency] = useState<FiatCurrency>("KRW");
  const [buyAmount, setBuyAmount] = useState("1,500,000");
  const [withdrawAmount, setWithdrawAmount] = useState("1,000");
  const [isPartnerModalOpen, setIsPartnerModalOpen] = useState(false);

  const buyQuote = useMemo(() => {
    const amount = parseAmount(buyAmount);
    const rate = demoRates[buyCurrency];
    const fee = amount * 0.0075;
    return { fee, receivedUsdc: rate ? (amount - fee) / rate : 0, rate };
  }, [buyAmount, buyCurrency]);
  const withdrawalQuote = useMemo(() => {
    const amount = parseAmount(withdrawAmount);
    const rate = demoRates[withdrawCurrency];
    const fee = amount * 0.0075;
    return { fee, receivedFiat: (amount - fee) * rate, rate };
  }, [withdrawAmount, withdrawCurrency]);
  const isBuy = mode === "buy";
  const isInvestorVariant = variant === "investor";
  const accentIconClass = variant === "investor" ? "settings-card__icon--purple" : "settings-card__icon--blue";

  return (
    <section className={`funds-conversion-page${isInvestorVariant ? " funds-conversion-page--investor" : ""}`}>
      <header className="page-heading">
        <div>
          <h1>{t("Funds conversion", "자금 전환")}</h1>
          <p>{t("Preview how USDC can move between your business and a financial partner.", "외부 금융 파트너를 통한 법정화폐와 USDC 전환 흐름을 미리 확인하세요.")}</p>
        </div>
        {!isInvestorVariant && <span className="funds-conversion-status"><CheckCircle size={14} weight="fill" aria-hidden="true" />{t("Partner flow preview", "파트너 연동 흐름 미리보기")}</span>}
      </header>

      {!isInvestorVariant && (
        <aside className="funds-conversion-notice">
          <Info size={18} weight="fill" aria-hidden="true" />
          <p>{t("Funds conversion is provided through external financial partners. Actual exchange rates and fees may vary at the partner's time of processing.", "자금 전환은 외부 금융 파트너를 통해 제공됩니다. 실제 환율과 수수료는 파트너사의 처리 시점에 따라 달라질 수 있습니다.")}</p>
        </aside>
      )}

      <div className="funds-conversion-tabs" role="tablist" aria-label={t("Funds conversion type", "자금 전환 유형")}>
        <button className={isBuy ? "is-active" : ""} type="button" role="tab" aria-selected={isBuy} onClick={() => setMode("buy")}>
          <Coins size={18} weight={isBuy ? "fill" : "regular"} aria-hidden="true" />
          <span>{t("Buy USDC", "USDC 구매")}</span><small>Fiat → USDC</small>
        </button>
        <button className={!isBuy ? "is-active" : ""} type="button" role="tab" aria-selected={!isBuy} onClick={() => setMode("withdraw")}>
          <Bank size={18} weight={!isBuy ? "fill" : "regular"} aria-hidden="true" />
          <span>{t("Withdraw USDC", "USDC 출금")}</span><small>USDC → Fiat</small>
        </button>
      </div>

      <article className="funds-conversion-card">
        <header className="settings-card__header">
            <span className={`settings-card__icon ${accentIconClass}`} aria-hidden="true"><ArrowsLeftRight size={19} weight="bold" /></span>
          <div>
            <h2>{isBuy ? t("Buy USDC", "USDC 구매") : t("Withdraw USDC", "USDC 출금")}</h2>
            <p>{isBuy ? t("Fiat to USDC through a settlement partner", "외부 정산 파트너를 통한 Fiat → USDC") : t("USDC to fiat through a settlement partner", "외부 정산 파트너를 통한 USDC → Fiat")}</p>
          </div>
          {!isInvestorVariant && <span className="funds-conversion-mock">{t("Demo quote", "Demo 견적")}</span>}
        </header>

        {isBuy ? (
          <div className="funds-conversion-form">
            <label className="funds-conversion-field">
              <span>{t("Amount to convert", "전환할 금액")}</span>
              <div className="funds-conversion-input"><input inputMode="decimal" value={buyAmount} onChange={(event) => setBuyAmount(event.target.value)} /><strong>{buyCurrency}</strong></div>
            </label>
            <label className="funds-conversion-field">
              <span>{t("Payment currency", "지급 통화")}</span>
              <select value={buyCurrency} onChange={(event) => setBuyCurrency(event.target.value as FiatCurrency)}>
                <option value="KRW">KRW · Korean won</option><option value="USD">USD · US dollar</option><option value="JPY">JPY · Japanese yen</option>
              </select>
            </label>
            <QuoteSummary
              amountLabel={t("Estimated USDC received", "예상 수령 USDC")}
              amount={formatAmount(buyQuote.receivedUsdc, 4) + " USDC"}
              rate={"1 USDC ≈ " + buyCurrency + " " + formatAmount(buyQuote.rate, 2)}
              fee={buyCurrency + " " + formatAmount(buyQuote.fee, 2) + " · 0.75%"}
            />
          </div>
        ) : (
          <div className="funds-conversion-form">
            <div className="funds-conversion-balance"><span>{t("Current USDC balance", "현재 USDC 잔액")}</span><strong>3,240.50 USDC</strong><small>{t("Demo balance shown for this preview", "본 화면에서는 Demo 잔액으로 표시됩니다.")}</small></div>
            <label className="funds-conversion-field">
              <span>{t("USDC to convert", "전환할 USDC")}</span>
              <div className="funds-conversion-input"><input inputMode="decimal" value={withdrawAmount} onChange={(event) => setWithdrawAmount(event.target.value)} /><strong>USDC</strong></div>
            </label>
            <label className="funds-conversion-field">
              <span>{t("Receiving currency", "수령 통화")}</span>
              <select value={withdrawCurrency} onChange={(event) => setWithdrawCurrency(event.target.value as FiatCurrency)}>
                <option value="KRW">KRW · Korean won</option><option value="USD">USD · US dollar</option><option value="JPY">JPY · Japanese yen</option>
              </select>
            </label>
            <QuoteSummary
              amountLabel={t("Estimated amount received", "예상 수령금액")}
              amount={withdrawCurrency + " " + formatAmount(withdrawalQuote.receivedFiat, 2)}
              rate={"1 USDC ≈ " + withdrawCurrency + " " + formatAmount(withdrawalQuote.rate, 2)}
              fee={formatAmount(withdrawalQuote.fee, 4) + " USDC · 0.75%"}
            />
          </div>
        )}

        <footer className="funds-conversion-footer">
          <div><span>{t("External partner", "외부 파트너")}</span><strong>{t("Settlement partner connection · Planned", "정산 파트너 연동 · 준비 중")}</strong></div>
          <button type="button" className="primary-button" onClick={() => setIsPartnerModalOpen(true)}>{t("Continue", "계속하기")}</button>
        </footer>
      </article>

      {isPartnerModalOpen ? (
        <div className="funds-conversion-modal-backdrop" role="presentation">
          <section className="funds-conversion-modal" role="dialog" aria-modal="true" aria-labelledby="funds-conversion-modal-title">
            <button type="button" className="funds-conversion-modal__close" onClick={() => setIsPartnerModalOpen(false)} aria-label={t("Close", "닫기")}><X size={18} weight="bold" aria-hidden="true" /></button>
            <span className={`settings-card__icon ${accentIconClass}`} aria-hidden="true"><ArrowsLeftRight size={20} weight="bold" /></span>
            <h2 id="funds-conversion-modal-title">{t("Partner flow is being prepared", "외부 파트너 전환 기능을 준비 중입니다.")}</h2>
            <p>{t("This preview does not submit a payment, exchange funds, or create a blockchain transaction.", "이 화면은 결제·환전·블록체인 트랜잭션을 실행하지 않는 Demo 흐름입니다.")}</p>
            <button type="button" className="primary-button" onClick={() => setIsPartnerModalOpen(false)}>{t("Confirm", "확인")}</button>
          </section>
        </div>
      ) : null}
    </section>
  );
}
