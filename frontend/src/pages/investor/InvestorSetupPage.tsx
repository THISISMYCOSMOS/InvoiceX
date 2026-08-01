import { CaretDown, CheckCircle, Info, ShieldCheck, SlidersHorizontal, Vault } from "@phosphor-icons/react";
import bs58 from "bs58";
import { VersionedTransaction } from "@solana/web3.js";
import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { useState } from "react";
import { rwaApi, type MandatePolicyInput } from "../../api/rwa.api";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { useLanguage } from "../../i18n/LanguageContext";

const mockBuyerCompanies = [
  { name: "Prime Mobility", description: "Mobility", koreanDescription: "모빌리티" },
  { name: "Orbit Components", description: "Components", koreanDescription: "부품 제조" },
  { name: "Daon Logistics", description: "Logistics", koreanDescription: "물류" },
  { name: "Vertex Retail", description: "Retail", koreanDescription: "유통" },
] as const;

interface InvestmentPolicyDraft {
  totalLimit: string;
  perInvoiceLimit: string;
  buyerAllowlist: string[];
  minimumScore: string;
  maximumTerm: string;
  policyTerm: string;
}

const defaultPolicy: InvestmentPolicyDraft = {
  totalLimit: "5",
  perInvoiceLimit: "1",
  buyerAllowlist: ["Prime Mobility"],
  minimumScore: "80",
  maximumTerm: "120",
  policyTerm: "2026-12-31",
};

function parseAmount(value: string): number {
  return Number(value.replace(/[^\d]/g, ""));
}

function fromBase64(value: string): Uint8Array {
  return Uint8Array.from(window.atob(value), (character) => character.charCodeAt(0));
}

export function InvestorSetupPage() {
  const { t } = useLanguage();
  const { connection } = useConnection();
  const { connected, publicKey, signMessage, sendTransaction } = useWallet();
  const [policy, setPolicy] = useState(defaultPolicy);
  const [depositAmount, setDepositAmount] = useState("1");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDepositing, setIsDepositing] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [vaultBalance, setVaultBalance] = useState<number | null>(null);
  const [activeMandateId, setActiveMandateId] = useState<string | null>(null);
  const [isBuyerSelectOpen, setIsBuyerSelectOpen] = useState(false);

  const updatePolicy = <Key extends keyof InvestmentPolicyDraft>(key: Key, value: InvestmentPolicyDraft[Key]) => {
    setPolicy((current) => ({ ...current, [key]: value }));
    setActiveMandateId(null);
  };

  const toggleBuyer = (buyerName: string) => {
    setPolicy((current) => ({
      ...current,
      buyerAllowlist: current.buyerAllowlist.includes(buyerName)
        ? current.buyerAllowlist.filter((name) => name !== buyerName)
        : [...current.buyerAllowlist, buyerName],
    }));
    setActiveMandateId(null);
  };

  const createPolicy = (): MandatePolicyInput => ({
    totalInvestmentLimitUsdc: parseAmount(policy.totalLimit),
    perInvoiceLimitUsdc: parseAmount(policy.perInvoiceLimit),
    buyerAllowlist: policy.buyerAllowlist,
    minimumRiskScore: parseAmount(policy.minimumScore),
    maximumRemainingTermDays: parseAmount(policy.maximumTerm),
    expiresAt: policy.policyTerm,
  });

  const activateMandate = async () => {
    if (!publicKey || !signMessage) {
      setError(t("Connect a wallet that supports message signing first.", "메시지 서명을 지원하는 기관 지갑을 먼저 연결해 주세요."));
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      const policyInput = createPolicy();
      const ownerWalletAddress = publicKey.toBase58();
      const { canonicalMessage } = await rwaApi.prepareMandate(ownerWalletAddress, policyInput);
      const signature = await signMessage(new TextEncoder().encode(canonicalMessage));
      const mandate = await rwaApi.createMandate(ownerWalletAddress, policyInput, bs58.encode(signature));
      setActiveMandateId(mandate.id);
      setSuccess(t("Automatic investment authorization is active. Deposit demo stablecoins into Agent Vault to enable purchases.", "자동 투자 권한이 활성화되었습니다. Agent Vault에 테스트 스테이블코인을 예치하면 자동 매수가 시작됩니다."));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("Mandate signing failed.", "Mandate 서명에 실패했습니다."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const depositToVault = async () => {
    if (!publicKey || !sendTransaction) {
      setError(t("Connect an institution wallet first.", "기관 지갑을 먼저 연결해 주세요."));
      return;
    }

    const amountUsdc = parseAmount(depositAmount);
    if (!Number.isInteger(amountUsdc) || amountUsdc <= 0) {
      setError(t("Enter a valid whole-USDC amount.", "예치할 USDC 수량을 정수로 입력해 주세요."));
      return;
    }

    setError(null);
    setSuccess(null);
    setIsDepositing(true);
    try {
      const ownerWalletAddress = publicKey.toBase58();
      const prepared = await rwaApi.prepareVaultDeposit(ownerWalletAddress, amountUsdc);
      const transaction = VersionedTransaction.deserialize(fromBase64(prepared.transactionBase64));
      const signature = await sendTransaction(transaction, connection, {
        preflightCommitment: "confirmed",
      });
      await connection.confirmTransaction(signature, "confirmed");
      const vault = await rwaApi.confirmVaultDeposit(ownerWalletAddress, amountUsdc, signature);
      setVaultBalance(vault.availableUsdc);
      setSuccess(t("The deposit was confirmed. Treasury Agent will evaluate eligible issued RWAs automatically.", "예치가 확인되었습니다. Treasury Agent가 발행된 RWA를 기준에 따라 자동 평가합니다."));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("Vault deposit failed.", "Agent Vault 예치에 실패했습니다."));
    } finally {
      setIsDepositing(false);
    }
  };

  return (
    <section className="investor-setup-page">
      <header className="investor-page-heading investor-setup-heading">
        <div>
          <p className="investor-breadcrumb">{t("Investor / Automatic investment", "투자자 / 자동 투자")}</p>
          <h1>{t("Automatic investment setup", "자동 투자 설정")}</h1>
          <p>{t("Set your investment criteria and authorize Treasury Agent with your institution wallet.", "투자 조건을 설정하고 기관 지갑으로 Treasury Agent의 자동 매수를 승인하세요.")}</p>
        </div>
        <span className="investor-setup-heading__step">{t("Step 1 of 2", "1 / 2 단계")}</span>
      </header>

      <div className="investor-setup-stack">
        <SolanaWalletConnection
          title={t("Institution wallet", "기관 지갑")}
          description={t("Use this wallet to authorize the investment mandate and deposit demo stablecoins into Agent Vault.", "이 지갑으로 투자 Mandate를 승인하고 Agent Vault에 테스트 스테이블코인을 예치합니다.")}
          onWalletDisconnected={() => {
            setSuccess(null);
            setVaultBalance(null);
            setActiveMandateId(null);
          }}
        />

        <section className="investor-setup-policy-card">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><ShieldCheck size={18} weight="bold" /></span>
            <div>
              <h2>{t("Automatic investment authorization", "자동 투자 권한")}</h2>
              <p>{t("Authorize Treasury Agent to execute an eligible RWA purchase from your Agent Vault.", "Treasury Agent가 Agent Vault에서 조건을 충족한 RWA를 자동 매수하도록 승인합니다.")}</p>
            </div>
            <span className={`investor-setup-draft ${activeMandateId ? "is-active" : ""}`}>{activeMandateId ? t("Authorized", "승인됨") : t("Signature required", "서명 필요")}</span>
          </header>

          <div className="investor-authorization-card__body">
            <dl className="investor-authorization-summary">
              <div><dt>{t("Authorization format", "권한 형식")}</dt><dd>{t("AP2 Mandate", "AP2 Mandate")}</dd></div>
              <div><dt>{t("Authorized agent", "실행 에이전트")}</dt><dd>Treasury Agent</dd></div>
              <div><dt>{t("Payment source", "결제 재원")}</dt><dd>Agent Vault · USDC</dd></div>
              <div><dt>{t("Applicable criteria", "적용 조건")}</dt><dd>{t("Investment criteria below", "아래 투자 조건")}</dd></div>
            </dl>
            <footer>
              <p><Info size={15} weight="fill" aria-hidden="true" />{t("The signature records your current investment criteria. Updating them requires a new signature.", "현재 투자 조건을 포함해 서명합니다. 조건을 변경하면 다시 서명해야 합니다.")}</p>
              <button className="investor-primary-button" type="button" disabled={!connected || isSubmitting} onClick={() => void activateMandate()}>
                <ShieldCheck size={15} weight="fill" aria-hidden="true" />
                {isSubmitting ? t("Waiting for signature...", "지갑 서명 대기 중...") : activeMandateId ? t("Re-sign authorization", "권한 다시 서명") : t("Sign authorization", "권한 서명")}
              </button>
            </footer>
          </div>
        </section>

        <section className="investor-setup-policy-card">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><SlidersHorizontal size={18} weight="bold" /></span>
            <div>
              <h2>{t("Investment criteria", "투자 조건")}</h2>
              <p>{t("Treasury Agent evaluates each invoice against the criteria you sign.", "Treasury Agent는 서명한 조건을 기준으로 각 인보이스를 평가합니다.")}</p>
            </div>
            <span className="investor-setup-draft">{activeMandateId ? t("Signed", "서명 완료") : t("Needs signature", "서명 대기")}</span>
          </header>

          <div className="investor-policy-form">
            <div className="investor-policy-form__grid">
              <label htmlFor="totalLimit"><span>{t("Total investment limit", "총 투자 한도")}</span><div><input id="totalLimit" inputMode="numeric" value={policy.totalLimit} onChange={(event) => updatePolicy("totalLimit", event.target.value)} /><small>USDC</small></div></label>
              <label htmlFor="perInvoiceLimit"><span>{t("Maximum per invoice", "인보이스당 최대 금액")}</span><div><input id="perInvoiceLimit" inputMode="numeric" value={policy.perInvoiceLimit} onChange={(event) => updatePolicy("perInvoiceLimit", event.target.value)} /><small>USDC</small></div></label>
              <div className="investor-policy-multiselect">
                <span id="buyerAllowlist-label">{t("Buyer allowlist", "구매기업 허용 목록")}</span>
                <button
                  type="button"
                  className="investor-policy-multiselect__trigger"
                  aria-labelledby="buyerAllowlist-label"
                  aria-haspopup="listbox"
                  aria-expanded={isBuyerSelectOpen}
                  onClick={() => setIsBuyerSelectOpen((current) => !current)}
                >
                  <span>
                    {policy.buyerAllowlist.length === 0
                      ? t("Select buyers", "구매기업 선택")
                      : policy.buyerAllowlist.length === 1
                        ? policy.buyerAllowlist[0]
                        : t(`${policy.buyerAllowlist.length} buyers selected`, `${policy.buyerAllowlist.length}개 기업 선택됨`)}
                  </span>
                  <CaretDown size={15} weight="bold" aria-hidden="true" />
                </button>
                {isBuyerSelectOpen && (
                  <div className="investor-policy-multiselect__menu" role="listbox" aria-multiselectable="true">
                    {mockBuyerCompanies.map((buyer) => {
                      const isSelected = policy.buyerAllowlist.includes(buyer.name);
                      return (
                        <label key={buyer.name} className={isSelected ? "is-selected" : ""}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleBuyer(buyer.name)}
                          />
                          <span className="investor-policy-multiselect__company">
                            <span className="investor-policy-multiselect__company-mark" aria-hidden="true">{buyer.name.slice(0, 1)}</span>
                            <span><strong>{buyer.name}</strong><small>{t(buyer.description, buyer.koreanDescription)}</small></span>
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
                <small>{t("Select one or more buyer companies.", "구매기업을 하나 이상 선택하세요.")}</small>
              </div>
              <label htmlFor="minimumScore"><span>{t("Minimum Risk Score", "최소 위험 점수")}</span><div><input id="minimumScore" inputMode="numeric" value={policy.minimumScore} onChange={(event) => updatePolicy("minimumScore", event.target.value)} /><small>/ 100</small></div></label>
              <label htmlFor="maximumTerm"><span>{t("Maximum remaining term", "최대 잔존 만기")}</span><div><input id="maximumTerm" inputMode="numeric" value={policy.maximumTerm} onChange={(event) => updatePolicy("maximumTerm", event.target.value)} /><small>{t("days", "일")}</small></div></label>
              <label htmlFor="policyTerm"><span>{t("Policy expiry", "정책 만료일")}</span><div><input id="policyTerm" type="date" value={policy.policyTerm} onChange={(event) => updatePolicy("policyTerm", event.target.value)} /></div></label>
            </div>

            <footer>
              <p><Info size={15} weight="fill" aria-hidden="true" />{t("Changes take effect after you sign the automatic investment authorization above.", "변경한 조건은 위 자동 투자 권한에 다시 서명하면 적용됩니다.")}</p>
            </footer>
          </div>
        </section>

        <section className="investor-setup-policy-card investor-vault-deposit-card">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><Vault size={18} weight="bold" /></span>
            <div>
              <h2>{t("Agent Vault deposit", "Agent Vault 예치")}</h2>
              <p>{t("Deposit the platform demo stablecoin. The agent can spend only this recorded vault balance.", "플랫폼 테스트 스테이블코인을 예치하세요. Agent는 이 Vault 잔액 안에서만 매수합니다.")}</p>
            </div>
            {vaultBalance !== null && <span className="investor-setup-draft">{vaultBalance.toLocaleString()} USDC</span>}
          </header>
          <div className="investor-vault-deposit-card__body">
            <label htmlFor="vaultDeposit"><span>{t("Deposit amount", "예치 금액")}</span><div><input id="vaultDeposit" inputMode="numeric" value={depositAmount} onChange={(event) => setDepositAmount(event.target.value)} /><small>USDC</small></div></label>
            <button className="investor-primary-button" type="button" disabled={!connected || isDepositing} onClick={() => void depositToVault()}>
              <Vault size={15} weight="fill" aria-hidden="true" />
              {isDepositing ? t("Confirming deposit...", "예치 확인 중...") : t("Sign Vault deposit", "Vault 예치 서명")}
            </button>
          </div>
        </section>

        {success && <p className="investor-setup-success" role="status"><CheckCircle size={15} weight="fill" aria-hidden="true" />{success}</p>}
        {error && <p className="wallet-error" role="alert">{error}</p>}
      </div>
    </section>
  );
}
