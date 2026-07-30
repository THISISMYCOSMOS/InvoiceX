import { useState } from "react";
import { useLanguage } from "../../i18n/LanguageContext";

export function InvestorSetupPage() {
  const [submitted, setSubmitted] = useState(false);
  const { t } = useLanguage();

  return (
    <section>
      <h1>{t("Investor Vault and AP2 Mandate setup", "Investor Vault 및 AP2 위임 설정")}</h1>
      <p>{t("Institution wallet", "기관 지갑 주소")}: DEMO_INVESTOR_WALLET</p>
      <p>{t("Vault address", "Vault 주소")}: DEMO_AGENT_VAULT</p>
      <p>{t("Vault USDC balance", "Vault USDC 잔액")}: 50,000 USDC</p>
      <form onSubmit={(event) => { event.preventDefault(); setSubmitted(true); }}>
        <label>
          {t("USDC deposit", "USDC 예치 금액")}
          <input name="deposit" type="number" min="0" defaultValue="50000" />
        </label>
        <p>
          {t(
            "Gasless fees are sponsored by the Sponsor Wallet. The investor wallet may hold 0 SOL.",
            "Gasless 수수료는 Sponsor Wallet이 지원하며 투자자 지갑의 SOL 잔액은 0이어도 됩니다.",
          )}
        </p>
        <label>
          {t("Total investment limit", "총 투자 한도")}
          <input name="totalLimit" defaultValue="50000" />
        </label>
        <label>
          {t("Maximum per invoice", "인보이스당 최대 투자 금액")}
          <input name="perInvoiceLimit" defaultValue="20000" />
        </label>
        <label>
          {t("Buyer Allowlist", "구매기업 허용 목록")}
          <input name="buyerAllowlist" defaultValue="BUYER_PRIME" />
        </label>
        <label>
          {t("Minimum Risk Score", "최소 위험 점수")}
          <input name="minimumScore" defaultValue="80" />
        </label>
        <label>
          {t("Maximum remaining term", "최대 잔존 만기")}
          <input name="maximumTerm" defaultValue={t("120 days", "120일")} />
        </label>
        <label>
          {t("Policy expiry", "정책 만료일")}
          <input name="policyTerm" defaultValue="2026-12-31" />
        </label>
        <button type="submit">
          {t("Request AP2 Mandate signature", "AP2 위임 서명 요청")}
        </button>
      </form>
      {submitted && (
        <p role="status">
          {t(
            "Setup values are ready for AP2 Mandate API integration.",
            "AP2 Mandate API 연동을 위한 설정 값이 준비되었습니다.",
          )}
        </p>
      )}
      <p>{t("Mandate ID", "위임 ID")}: DEMO-MANDATE-001</p>
      <p>{t("Policy hash", "정책 해시")}: demo-policy-v1</p>
      <p>{t("Mandate status", "위임 상태")}: ACTIVE</p>
    </section>
  );
}
