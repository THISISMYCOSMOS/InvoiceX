import { CheckCircle, Info, ShieldCheck, SlidersHorizontal } from "@phosphor-icons/react";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";
import { useInvestorMandate } from "../../hooks/useInvestorMandate";
import { useLanguage } from "../../i18n/LanguageContext";
import type { InvestorMandate } from "../../types/invoice";

function numberValue(form: FormData, name: string): number {
  return Number(form.get(name));
}

export function InvestorSetupPage() {
  const { t } = useLanguage();
  const dashboard = useInvestorDashboard();
  const { mandate, save } = useInvestorMandate();

  if (mandate.isLoading || dashboard.isLoading) return <LoadingState />;
  if (mandate.error || dashboard.error || !mandate.data || !dashboard.data) {
    return (
      <ErrorState
        error={mandate.error ?? dashboard.error ?? new Error(t("Mandate data not found.", "Mandate 데이터를 찾을 수 없습니다."))}
      />
    );
  }

  const current = mandate.data;
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next: InvestorMandate = {
      ...current,
      depositUsdc: numberValue(form, "deposit"),
      totalLimitUsdc: numberValue(form, "totalLimit"),
      perInvoiceLimitUsdc: numberValue(form, "perInvoiceLimit"),
      buyerAllowlist: String(form.get("buyerAllowlist") ?? "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
      minimumRiskScore: numberValue(form, "minimumScore"),
      maximumTermDays: numberValue(form, "maximumTerm"),
      policyExpiresOn: String(form.get("policyTerm") ?? ""),
      status: "ACTIVE",
    };
    save.mutate(next);
  };

  return (
    <section className="investor-setup-page">
      <header className="investor-page-heading investor-setup-heading">
        <div>
          <p className="investor-breadcrumb">{t("Investor / Setup", "투자자 / 투자 위임")}</p>
          <h1>{t("Investment mandate setup", "투자 위임 설정")}</h1>
          <p>
            {t(
              "Connect your institution wallet and set the investment guardrails used by Treasury Agent.",
              "기관 지갑을 연결하고 Treasury Agent가 따를 투자 기준을 설정하세요.",
            )}
          </p>
        </div>
        <span className="investor-setup-heading__step">{current.status}</span>
      </header>

      <div className="investor-setup-stack">
        <SolanaWalletConnection
          title={t("Institution wallet", "기관 지갑")}
          description={t(
            "Connect the institution wallet used to authorize future vault operations.",
            "향후 Vault 작업을 승인할 기관 지갑을 연결하세요.",
          )}
          onWalletConnected={() => undefined}
          onWalletDisconnected={() => undefined}
        />

        <section className="investor-setup-policy-card">
          <header>
            <span className="investor-setup-icon" aria-hidden="true">
              <SlidersHorizontal size={18} weight="bold" />
            </span>
            <div>
              <h2>{t("Investment policy", "투자 정책")}</h2>
              <p>
                {t("Set guardrails for eligible invoices.", "자동 투자할 인보이스의 기준을 설정합니다.")}
              </p>
            </div>
            <span className="investor-setup-draft">
              {dashboard.data.availableVaultUsdc.toLocaleString()} USDC
            </span>
          </header>

          <form className="investor-policy-form" onSubmit={submit}>
            <div className="investor-policy-form__grid">
              <label htmlFor="deposit">
                <span>{t("USDC deposit", "USDC 예치 금액")}</span>
                <div>
                  <input id="deposit" name="deposit" type="number" min="0" defaultValue={current.depositUsdc} required />
                  <small>USDC</small>
                </div>
              </label>
              <label htmlFor="totalLimit">
                <span>{t("Total investment limit", "총 투자 한도")}</span>
                <div>
                  <input id="totalLimit" name="totalLimit" type="number" min="0" defaultValue={current.totalLimitUsdc} required />
                  <small>USDC</small>
                </div>
              </label>
              <label htmlFor="perInvoiceLimit">
                <span>{t("Maximum per invoice", "인보이스당 최대 금액")}</span>
                <div>
                  <input id="perInvoiceLimit" name="perInvoiceLimit" type="number" min="1" defaultValue={current.perInvoiceLimitUsdc} required />
                  <small>USDC</small>
                </div>
              </label>
              <label htmlFor="buyerAllowlist">
                <span>{t("Buyer allowlist", "구매기업 허용 목록")}</span>
                <div>
                  <input id="buyerAllowlist" name="buyerAllowlist" defaultValue={current.buyerAllowlist.join(", ")} required />
                </div>
              </label>
              <label htmlFor="minimumScore">
                <span>{t("Minimum Risk Score", "최소 위험 점수")}</span>
                <div>
                  <input id="minimumScore" name="minimumScore" type="number" min="0" max="100" defaultValue={current.minimumRiskScore} required />
                  <small>/ 100</small>
                </div>
              </label>
              <label htmlFor="maximumTerm">
                <span>{t("Maximum remaining term", "최대 잔존 만기")}</span>
                <div>
                  <input id="maximumTerm" name="maximumTerm" type="number" min="1" defaultValue={current.maximumTermDays} required />
                  <small>{t("days", "일")}</small>
                </div>
              </label>
              <label htmlFor="policyTerm">
                <span>{t("Policy expiry", "정책 만료일")}</span>
                <div>
                  <input id="policyTerm" name="policyTerm" type="date" defaultValue={current.policyExpiresOn} required />
                </div>
              </label>
            </div>

            <footer>
              <p>
                <Info size={15} weight="fill" aria-hidden="true" />
                {t(
                  `Institution: ${dashboard.data.investorName} · Vault: ${dashboard.data.vaultAddress}`,
                  `기관: ${dashboard.data.investorName} · Vault: ${dashboard.data.vaultAddress}`,
                )}
              </p>
              <button className="investor-primary-button" type="submit" disabled={save.isPending}>
                <ShieldCheck size={15} weight="fill" aria-hidden="true" />
                {save.isPending
                  ? t("Saving AP2 Mandate...", "AP2 위임 저장 중...")
                  : t("Save AP2 Mandate", "AP2 위임 저장")}
              </button>
            </footer>
          </form>

          {save.isSuccess && (
            <p className="investor-setup-success" role="status">
              <CheckCircle size={15} weight="fill" aria-hidden="true" />
              {t("AP2 Mandate saved.", "AP2 위임을 저장했습니다.")}
            </p>
          )}
          {save.error && <ErrorState error={save.error} />}
        </section>
      </div>
    </section>
  );
}
