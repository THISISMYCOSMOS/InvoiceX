import { CaretDown, CheckCircle, Info, MagnifyingGlass, ShieldCheck, Signature, SlidersHorizontal, SquaresFour } from "@phosphor-icons/react";
import bs58 from "bs58";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { rwaApi, type InvestorMandate, type MandatePolicyInput } from "../../api/rwa.api";
import { useCurrentPrivyAccount } from "../../auth/currentAccount";
import { useSignupAuth } from "../../auth/SignupAuthContext";
import { useLanguage } from "../../i18n/LanguageContext";

const fallbackBuyerCompanies = ["Prime Mobility", "Orbit Components", "Daon Logistics", "Vertex Retail"] as const;

interface InvestmentPolicyDraft {
  totalLimit: string;
  perInvoiceLimit: string;
  buyerAllowlist: string[];
  minimumScore: string;
  maximumTerm: string;
  policyTerm: string;
}

type PolicyTab = "mandate" | "conditions";

const defaultPolicy: InvestmentPolicyDraft = {
  totalLimit: "1",
  perInvoiceLimit: "1",
  buyerAllowlist: ["Prime Mobility"],
  minimumScore: "80",
  maximumTerm: "120",
  policyTerm: "2026-12-31",
};

function parseAmount(value: string): number {
  return Number(value.replace(/[^\d]/g, ""));
}

function policyFromMandate(policy: MandatePolicyInput): InvestmentPolicyDraft {
  return {
    totalLimit: String(policy.totalInvestmentLimitUsdc),
    perInvoiceLimit: String(policy.perInvoiceLimitUsdc),
    buyerAllowlist: policy.buyerAllowlist,
    minimumScore: String(policy.minimumRiskScore),
    maximumTerm: String(policy.maximumRemainingTermDays),
    policyTerm: policy.expiresAt,
  };
}

export function InvestorInvestmentPolicyPage() {
  const { t } = useLanguage();
  const currentAccount = useCurrentPrivyAccount();
  const { embeddedSolanaWalletReady, signEmbeddedSolanaMessage } = useSignupAuth();
  const [policy, setPolicy] = useState(defaultPolicy);
  const [buyerCompanies, setBuyerCompanies] = useState<readonly string[]>(fallbackBuyerCompanies);
  const [activeMandateId, setActiveMandateId] = useState<string | null>(null);
  const [hasPolicyChanges, setHasPolicyChanges] = useState(false);
  const [isBuyerSelectOpen, setIsBuyerSelectOpen] = useState(false);
  const [buyerSearch, setBuyerSearch] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<PolicyTab>("conditions");
  const embeddedWalletAddress = currentAccount?.walletAddress ?? null;
  const ownerWalletAddress = embeddedWalletAddress;
  const hasEmbeddedWallet = Boolean(embeddedWalletAddress);
  const canSignWithEmbeddedWallet = Boolean(embeddedSolanaWalletReady && embeddedWalletAddress);

  useEffect(() => {
    let cancelled = false;
    void rwaApi.getInvestmentCriteriaBuyers()
      .then((buyers) => {
        if (!cancelled && buyers.length > 0) setBuyerCompanies(buyers.map((buyer) => buyer.name));
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!ownerWalletAddress) {
      setActiveMandateId(null);
      return;
    }
    let cancelled = false;
    void rwaApi.getActiveMandate(ownerWalletAddress)
      .then((mandate: InvestorMandate | null) => {
        if (cancelled || mandate === null) return;
        setPolicy(policyFromMandate(mandate.policy));
        setActiveMandateId(mandate.id);
        setHasPolicyChanges(false);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "저장된 투자 권한을 불러오지 못했습니다.");
      });
    return () => { cancelled = true; };
  }, [ownerWalletAddress]);

  const updatePolicy = <Key extends keyof InvestmentPolicyDraft>(key: Key, value: InvestmentPolicyDraft[Key]) => {
    setPolicy((current) => ({ ...current, [key]: value }));
    if (activeMandateId) setHasPolicyChanges(true);
  };

  const toggleBuyer = (buyerName: string) => {
    setPolicy((current) => ({
      ...current,
      buyerAllowlist: current.buyerAllowlist.includes(buyerName)
        ? current.buyerAllowlist.filter((name) => name !== buyerName)
        : [...current.buyerAllowlist, buyerName],
    }));
    if (activeMandateId) setHasPolicyChanges(true);
  };

  const activateMandate = async () => {
    if (!embeddedWalletAddress || !embeddedSolanaWalletReady) {
      setError(t("Your embedded wallet is not ready for signing yet.", "임베디드 지갑을 아직 서명에 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."));
      return;
    }
    const signingWalletAddress = embeddedWalletAddress;
    if (policy.buyerAllowlist.length === 0) {
      setError(t("Select at least one buyer company before signing.", "서명하기 전에 구매기업을 하나 이상 선택해 주세요."));
      return;
    }
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      const policyInput: MandatePolicyInput = {
        totalInvestmentLimitUsdc: parseAmount(policy.totalLimit),
        perInvoiceLimitUsdc: parseAmount(policy.perInvoiceLimit),
        buyerAllowlist: policy.buyerAllowlist,
        minimumRiskScore: parseAmount(policy.minimumScore),
        maximumRemainingTermDays: parseAmount(policy.maximumTerm),
        expiresAt: policy.policyTerm,
      };
      const { canonicalMessage } = await rwaApi.prepareMandate(signingWalletAddress, policyInput);
      const signature = await signEmbeddedSolanaMessage(signingWalletAddress, new TextEncoder().encode(canonicalMessage));
      const mandate = await rwaApi.createMandate(signingWalletAddress, policyInput, bs58.encode(signature));
      setActiveMandateId(mandate.id);
      setHasPolicyChanges(false);
      setSuccess(t("Investment Policy is signed and active.", "Investment Policy가 서명되어 활성화되었습니다."));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("Mandate signing failed.", "Mandate 서명에 실패했습니다."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const mandateState = activeMandateId
    ? hasPolicyChanges ? "CHANGES_REQUIRE_SIGNATURE" : "ACTIVE"
    : "SIGNATURE_REQUIRED";
  const mandateStateLabel = mandateState === "ACTIVE"
    ? t("Active", "활성")
    : mandateState === "CHANGES_REQUIRE_SIGNATURE" ? t("Re-sign required", "재서명 필요") : t("Signature required", "서명 필요");
  const mandateActionLabel = mandateState === "ACTIVE"
    ? t("Re-sign & save policy", "변경사항 저장 및 재서명")
    : t("Sign & save policy", "변경사항 저장 및 서명");

  return (
    <section className="investor-setup-page">
      <header className="investor-page-heading investor-setup-heading">
        <div>
          <p className="investor-breadcrumb">{t("Investor / Investment Policy", "투자자 / 투자 정책")}</p>
          <h1>{t("Investment Policy", "투자 정책")}</h1>
          <p>{t("Define the conditions Treasury Agent must meet before investing from your Vault.", "Treasury Agent가 Vault 자금으로 투자하기 전에 충족해야 할 조건을 관리하세요.")}</p>
        </div>
      </header>

      <div className="investor-activity-filters investor-policy-tabs" role="tablist" aria-label={t("Investment Policy sections", "투자 정책 구분")}>
        <button
          id="investment-conditions-tab"
          type="button"
          role="tab"
          aria-selected={activeTab === "conditions"}
          aria-controls="investment-conditions-panel"
          className={activeTab === "conditions" ? "is-active" : ""}
          onClick={() => setActiveTab("conditions")}
        >
          {t("Investment conditions", "투자 조건")}
        </button>
        <button
          id="investment-mandate-tab"
          type="button"
          role="tab"
          aria-selected={activeTab === "mandate"}
          aria-controls="investment-mandate-panel"
          className={activeTab === "mandate" ? "is-active" : ""}
          onClick={() => setActiveTab("mandate")}
        >
          {t("Mandate", "Mandate")}
        </button>
      </div>

      <div className="investor-setup-stack">
        {activeTab === "mandate" ? (
          <section id="investment-mandate-panel" className="investor-setup-policy-card" role="tabpanel" aria-labelledby="investment-mandate-tab">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><ShieldCheck size={18} weight="bold" /></span>
            <div>
              <h2>{t("Investment Mandate", "투자 Mandate")}</h2>
              <p>{t("An embedded-wallet-signed authorization for Treasury Agent to invest within the policy below.", "아래 정책 범위에서 Treasury Agent가 투자하도록 승인하는 임베디드 지갑 서명 권한입니다.")}</p>
            </div>
            <span className={`investor-setup-draft ${mandateState === "ACTIVE" ? "is-active" : mandateState === "CHANGES_REQUIRE_SIGNATURE" ? "is-resign-required" : ""}`}>{mandateStateLabel}</span>
          </header>
          <div className="investor-authorization-card__body">
            <dl className="investor-authorization-summary">
              <div><dt>{t("Authorization", "자동 투자 권한")}</dt><dd>{t("Embedded wallet-signed Mandate", "임베디드 지갑 서명 Mandate")}</dd></div>
              <div><dt>{t("Authorized agent", "실행 에이전트")}</dt><dd>Treasury Agent</dd></div>
              <div><dt>{t("Payment source", "결제 재원")}</dt><dd>Vault · USDC</dd></div>
              <div><dt>{t("Mandate status", "Mandate 상태")}</dt><dd>{mandateStateLabel}</dd></div>
            </dl>
            <footer>
              <p><Info size={15} weight="fill" aria-hidden="true" />{t("Policy changes apply only after your embedded wallet signs them.", "정책 변경사항은 임베디드 지갑으로 서명한 뒤에만 적용됩니다.")}</p>
              {hasEmbeddedWallet ? <span className="investor-setup-draft is-active">{t("Embedded wallet active", "임베디드 지갑 사용 중")}</span> : <Link className="investor-secondary-button" to="/investor/profile">{t("Review embedded wallet in Profile", "Profile에서 임베디드 지갑 확인")}</Link>}
            </footer>
          </div>
          </section>
        ) : (

          <section id="investment-conditions-panel" className="investor-setup-policy-card investor-investment-criteria-card" role="tabpanel" aria-labelledby="investment-conditions-tab">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><SlidersHorizontal size={18} weight="bold" /></span>
            <div>
              <h2>{t("Investment Conditions", "투자 조건")}</h2>
              <p>{t("Treasury Agent evaluates each invoice against the conditions you sign.", "Treasury Agent는 서명한 조건을 기준으로 각 인보이스를 평가합니다.")}</p>
            </div>
          </header>
          <div className="investor-policy-form">
            <div className="investor-policy-form__grid">
              <label htmlFor="totalLimit"><span>{t("Total investment limit", "총 미상환 투자잔액 한도")}</span><div><input id="totalLimit" inputMode="numeric" value={policy.totalLimit} onChange={(event) => updatePolicy("totalLimit", event.target.value)} /><small>USDC</small></div></label>
              <label htmlFor="perInvoiceLimit"><span>{t("Maximum per invoice", "건당 최대 투자금액")}</span><div><input id="perInvoiceLimit" inputMode="numeric" value={policy.perInvoiceLimit} onChange={(event) => updatePolicy("perInvoiceLimit", event.target.value)} /><small>USDC</small></div></label>
              <div className="investor-policy-multiselect">
                <span id="buyerAllowlist-label">{t("Buyer allowlist", "Buyer Allowlist")}</span>
                <button type="button" className="investor-policy-multiselect__trigger" aria-labelledby="buyerAllowlist-label" aria-haspopup="listbox" aria-expanded={isBuyerSelectOpen} onClick={() => setIsBuyerSelectOpen((current) => !current)}>
                  <SquaresFour size={17} weight="fill" aria-hidden="true" />
                  <span>{policy.buyerAllowlist.length === 0 ? t("Select buyers", "구매기업 선택") : policy.buyerAllowlist.length === 1 ? policy.buyerAllowlist[0] : t(`${policy.buyerAllowlist.length} buyers selected`, `${policy.buyerAllowlist.length}개 기업 선택됨`)}</span>
                  <CaretDown size={15} weight="bold" aria-hidden="true" />
                </button>
                {isBuyerSelectOpen ? (
                  <div className="investor-policy-multiselect__menu">
                    <label className="investor-policy-multiselect__search"><span className="sr-only">{t("Search buyer companies", "구매기업 검색")}</span><input value={buyerSearch} onChange={(event) => setBuyerSearch(event.target.value)} placeholder={t("Search companies", "기업 검색")} /><MagnifyingGlass size={17} aria-hidden="true" /></label>
                    <div className="investor-policy-multiselect__options" role="listbox" aria-multiselectable="true">
                      {buyerCompanies.filter((buyer) => buyer.toLowerCase().includes(buyerSearch.trim().toLowerCase())).map((buyer) => {
                        const isSelected = policy.buyerAllowlist.includes(buyer);
                        return <label key={buyer} className={isSelected ? "is-selected" : ""}><input type="checkbox" checked={isSelected} onChange={() => toggleBuyer(buyer)} /><span>{buyer}</span></label>;
                      })}
                    </div>
                  </div>
                ) : null}
                <small>{t("Select one or more buyer companies.", "구매기업을 하나 이상 선택하세요.")}</small>
              </div>
              <label htmlFor="minimumScore"><span>{t("Minimum Risk Score", "최소 Risk Score")}</span><div><input id="minimumScore" inputMode="numeric" value={policy.minimumScore} onChange={(event) => updatePolicy("minimumScore", event.target.value)} /><small>/ 100</small></div></label>
              <label htmlFor="maximumTerm"><span>{t("Maximum remaining term", "최대 잔존 만기")}</span><div><input id="maximumTerm" inputMode="numeric" value={policy.maximumTerm} onChange={(event) => updatePolicy("maximumTerm", event.target.value)} /><small>{t("days", "일")}</small></div></label>
              <label htmlFor="policyTerm"><span>{t("Policy expiry", "정책 만료일")}</span><div><input id="policyTerm" type="date" value={policy.policyTerm} onChange={(event) => updatePolicy("policyTerm", event.target.value)} /></div></label>
            </div>
            <footer>
              <p><Info size={15} weight="fill" aria-hidden="true" />{t("Saving asks your embedded wallet to sign the current Investment Policy.", "저장하면 임베디드 지갑으로 현재 Investment Policy의 서명을 요청합니다.")}</p>
              <button className="investor-primary-button" type="button" disabled={!canSignWithEmbeddedWallet || isSubmitting} onClick={() => void activateMandate()}>
                {isSubmitting ? t("Waiting for signature...", "지갑 서명 대기 중...") : <><Signature size={15} weight="fill" aria-hidden="true" />{mandateActionLabel}</>}
              </button>
            </footer>
          </div>
          </section>
        )}
        {success ? <p className="investor-setup-success" role="status"><CheckCircle size={15} weight="fill" aria-hidden="true" />{success}</p> : null}
        {error ? <p className="wallet-error" role="alert">{error}</p> : null}
      </div>
    </section>
  );
}
