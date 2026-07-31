import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
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
    return <ErrorState error={mandate.error ?? dashboard.error ?? new Error(t("Mandate data not found.", "Mandate 데이터를 찾을 수 없습니다."))} />;
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
    <section>
      <h1>{t("Investor Vault and AP2 Mandate setup", "Investor Vault 및 AP2 위임 설정")}</h1>
      <p>{t("Institution", "기관")}: {dashboard.data.investorName}</p>
      <p>{t("Vault address", "Vault 주소")}: {dashboard.data.vaultAddress}</p>
      <p>{t("Vault USDC balance", "Vault USDC 잔액")}: {dashboard.data.availableVaultUsdc.toLocaleString()} USDC</p>
      <form onSubmit={submit}>
        <label>
          {t("USDC deposit", "USDC 예치 금액")}
          <input name="deposit" type="number" min="0" defaultValue={current.depositUsdc} required />
        </label>
        <p>
          {t(
            "Gasless fees are sponsored by the Sponsor Wallet. The investor wallet may hold 0 SOL.",
            "Gasless 수수료는 Sponsor Wallet이 지원하며 투자자 지갑의 SOL 잔액은 0이어도 됩니다.",
          )}
        </p>
        <label>
          {t("Total investment limit", "총 투자 한도")}
          <input name="totalLimit" type="number" min="0" defaultValue={current.totalLimitUsdc} required />
        </label>
        <label>
          {t("Maximum per invoice", "인보이스당 최대 투자 금액")}
          <input name="perInvoiceLimit" type="number" min="1" defaultValue={current.perInvoiceLimitUsdc} required />
        </label>
        <label>
          {t("Buyer Allowlist", "구매기업 허용 목록")}
          <input name="buyerAllowlist" defaultValue={current.buyerAllowlist.join(", ")} required />
        </label>
        <label>
          {t("Minimum Risk Score", "최소 위험 점수")}
          <input name="minimumScore" type="number" min="0" max="100" defaultValue={current.minimumRiskScore} required />
        </label>
        <label>
          {t("Maximum remaining term", "최대 잔존 만기")}
          <input name="maximumTerm" type="number" min="1" defaultValue={current.maximumTermDays} required />
        </label>
        <label>
          {t("Policy expiry", "정책 만료일")}
          <input name="policyTerm" type="date" defaultValue={current.policyExpiresOn} required />
        </label>
        <button type="submit" disabled={save.isPending}>
          {save.isPending
            ? t("Saving AP2 Mandate...", "AP2 위임 저장 중...")
            : t("Save AP2 Mandate", "AP2 위임 저장")}
        </button>
      </form>
      {save.isSuccess && (
        <p role="status">{t("AP2 Mandate saved.", "AP2 위임을 저장했습니다.")}</p>
      )}
      {save.error && <ErrorState error={save.error} />}
      <p>{t("Mandate ID", "위임 ID")}: {current.mandateId}</p>
      <p>{t("Policy hash", "정책 해시")}: {current.policyHash}</p>
      <p>{t("Mandate status", "위임 상태")}: {current.status}</p>
    </section>
  );
}
