import { CheckCircle, Info, ShieldCheck, SlidersHorizontal, Vault } from "@phosphor-icons/react";
import bs58 from "bs58";
import { VersionedTransaction } from "@solana/web3.js";
import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { useState } from "react";
import { rwaApi, type MandatePolicyInput } from "../../api/rwa.api";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { useLanguage } from "../../i18n/LanguageContext";

const defaultPolicy = {
  totalLimit: "50,000",
  perInvoiceLimit: "20,000",
  buyerAllowlist: "Prime Mobility",
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
  const [depositAmount, setDepositAmount] = useState("20000");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDepositing, setIsDepositing] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [vaultBalance, setVaultBalance] = useState<number | null>(null);

  const updatePolicy = (key: keyof typeof defaultPolicy, value: string) => {
    setPolicy((current) => ({ ...current, [key]: value }));
  };

  const createPolicy = (): MandatePolicyInput => ({
    totalInvestmentLimitUsdc: parseAmount(policy.totalLimit),
    perInvoiceLimitUsdc: parseAmount(policy.perInvoiceLimit),
    buyerAllowlist: policy.buyerAllowlist.split(",").map((name) => name.trim()).filter(Boolean),
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
      await rwaApi.createMandate(ownerWalletAddress, policyInput, bs58.encode(signature));
      setSuccess(t("The investment mandate is active. Deposit demo stablecoins into Agent Vault to enable automatic purchases.", "투자 Mandate가 활성화되었습니다. Agent Vault에 테스트 스테이블코인을 예치하면 자동 매수가 시작됩니다."));
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
      const signature = await sendTransaction(transaction, connection);
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
          <p className="investor-breadcrumb">{t("Investor / Setup", "투자자 / 투자 위임")}</p>
          <h1>{t("Investment mandate setup", "투자 위임 설정")}</h1>
          <p>{t("Connect your institution wallet and set the investment guardrails used by Treasury Agent.", "기관 지갑을 연결하고 Treasury Agent가 따를 투자 기준을 설정하세요.")}</p>
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
          }}
        />

        <section className="investor-setup-policy-card">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><SlidersHorizontal size={18} weight="bold" /></span>
            <div>
              <h2>{t("Investment policy", "투자 정책")}</h2>
              <p>{t("Treasury Agent buys only invoices that satisfy every signed guardrail.", "Treasury Agent는 서명한 모든 기준을 통과한 인보이스만 자동 매수합니다.")}</p>
            </div>
            <span className="investor-setup-draft">{t("Wallet signature", "지갑 서명")}</span>
          </header>

          <div className="investor-policy-form">
            <div className="investor-policy-form__grid">
              <label htmlFor="totalLimit"><span>{t("Total investment limit", "총 투자 한도")}</span><div><input id="totalLimit" inputMode="numeric" value={policy.totalLimit} onChange={(event) => updatePolicy("totalLimit", event.target.value)} /><small>USDC</small></div></label>
              <label htmlFor="perInvoiceLimit"><span>{t("Maximum per invoice", "인보이스당 최대 금액")}</span><div><input id="perInvoiceLimit" inputMode="numeric" value={policy.perInvoiceLimit} onChange={(event) => updatePolicy("perInvoiceLimit", event.target.value)} /><small>USDC</small></div></label>
              <label htmlFor="buyerAllowlist"><span>{t("Buyer allowlist", "구매기업 허용 목록")}</span><div><input id="buyerAllowlist" value={policy.buyerAllowlist} onChange={(event) => updatePolicy("buyerAllowlist", event.target.value)} /></div></label>
              <label htmlFor="minimumScore"><span>{t("Minimum Risk Score", "최소 위험 점수")}</span><div><input id="minimumScore" inputMode="numeric" value={policy.minimumScore} onChange={(event) => updatePolicy("minimumScore", event.target.value)} /><small>/ 100</small></div></label>
              <label htmlFor="maximumTerm"><span>{t("Maximum remaining term", "최대 잔존 만기")}</span><div><input id="maximumTerm" inputMode="numeric" value={policy.maximumTerm} onChange={(event) => updatePolicy("maximumTerm", event.target.value)} /><small>{t("days", "일")}</small></div></label>
              <label htmlFor="policyTerm"><span>{t("Policy expiry", "정책 만료일")}</span><div><input id="policyTerm" type="date" value={policy.policyTerm} onChange={(event) => updatePolicy("policyTerm", event.target.value)} /></div></label>
            </div>

            <footer>
              <p><Info size={15} weight="fill" aria-hidden="true" />{t("Signing activates this policy on the server; no private key is sent to InvoiceX.", "서명하면 이 정책이 서버에서 활성화되며 개인키는 InvoiceX에 전달되지 않습니다.")}</p>
              <button className="investor-primary-button" type="button" disabled={!connected || isSubmitting} onClick={() => void activateMandate()}>
                <ShieldCheck size={15} weight="fill" aria-hidden="true" />
                {isSubmitting ? t("Waiting for signature...", "지갑 서명 대기 중...") : t("Sign and activate mandate", "서명하고 Mandate 활성화")}
              </button>
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
