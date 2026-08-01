import { CheckCircle, Coins, Info, ShieldCheck, SlidersHorizontal } from "@phosphor-icons/react";
import { useState } from "react";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { useConnectedSolanaWallet } from "../../hooks/useConnectedSolanaWallet";
import { useInvestorDeposit } from "../../hooks/useInvestorDeposit";
import { useLanguage } from "../../i18n/LanguageContext";

export function InvestorSetupPage() {
  const [submitted, setSubmitted] = useState(false);
  const [depositAmount, setDepositAmount] = useState(20);
  const { t } = useLanguage();
  const connectedWallet = useConnectedSolanaWallet();
  const deposit = useInvestorDeposit();

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
        <span className="investor-setup-heading__step">{t("Step 1 of 2", "1 / 2 단계")}</span>
      </header>

      <div className="investor-setup-stack">
        <SolanaWalletConnection
          title={t("Institution wallet", "기관 지갑")}
          description={t(
            "The connected wallet will be used later for Agent Vault deposits and auto-invest authorization signatures.",
            "연결한 지갑은 향후 Agent Vault 예치와 자동투자 권한 서명에 사용됩니다.",
          )}
          onWalletConnected={() => undefined}
          onWalletDisconnected={() => undefined}
        />

        <section className="investor-setup-policy-card">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><Coins size={18} weight="fill" /></span>
            <div>
              <h2>{t("Fund Agent Vault", "Agent Vault 예치")}</h2>
              <p>{t(
                "Deposit Devnet USDC from the connected investor wallet before automated funding.",
                "자동 투자 실행 전에 연결한 투자자 지갑에서 Devnet USDC를 예치합니다.",
              )}</p>
            </div>
            <span className="investor-setup-draft">Solana Devnet</span>
          </header>

          <form
            className="investor-policy-form"
            onSubmit={(event) => {
              event.preventDefault();
              deposit.mutate({ amountUsdc: depositAmount });
            }}
          >
            <div className="investor-policy-form__grid">
              <label htmlFor="depositAmount">
                <span>{t("Deposit amount", "예치 금액")}</span>
                <div>
                  <input
                    id="depositAmount"
                    name="depositAmount"
                    type="number"
                    min="1"
                    step="1"
                    value={depositAmount}
                    onChange={(event) => setDepositAmount(Number(event.target.value))}
                  />
                  <small>USDC</small>
                </div>
              </label>
              <div className="investor-deposit-wallet">
                <span>{t("Investor wallet", "투자자 지갑")}</span>
                <p>{connectedWallet.publicKey ?? t("Connect Account 2 first", "Account 2를 먼저 연결하세요")}</p>
              </div>
            </div>
            <footer>
              <p>
                <Info size={15} weight="fill" aria-hidden="true" />
                {t(
                  "MetaMask signs the transfer. InvoiceX never receives your private key.",
                  "전송은 MetaMask가 서명하며 InvoiceX는 개인키를 전달받지 않습니다.",
                )}
              </p>
              <button
                className="investor-primary-button"
                type="submit"
                disabled={!connectedWallet.connected || deposit.isPending || depositAmount < 1}
              >
                <Coins size={15} weight="fill" aria-hidden="true" />
                {deposit.isPending
                  ? t("Confirming deposit...", "예치 확인 중...")
                  : t("Deposit Devnet USDC", "Devnet USDC 예치")}
              </button>
            </footer>
          </form>

          {deposit.error ? (
            <p className="investor-setup-error" role="alert">
              {deposit.error instanceof Error ? deposit.error.message : t("Deposit failed.", "예치에 실패했습니다.")}
            </p>
          ) : null}
          {deposit.data ? (
            <p className="investor-setup-success" role="status">
              <CheckCircle size={15} weight="fill" aria-hidden="true" />
              {t(
                `${deposit.data.amountUsdc} USDC deposit confirmed.`,
                `${deposit.data.amountUsdc} USDC 예치가 확인되었습니다.`,
              )}{" "}
              <a href={deposit.data.explorerUrl} target="_blank" rel="noreferrer">
                {t("View transaction", "트랜잭션 보기")}
              </a>
            </p>
          ) : null}
        </section>

        <section className="investor-setup-policy-card">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><SlidersHorizontal size={18} weight="bold" /></span>
            <div>
              <h2>{t("Investment policy", "투자 정책")}</h2>
              <p>{t("Set guardrails for eligible invoices.", "자동 투자할 인보이스의 기준을 설정합니다.")}</p>
            </div>
            <span className="investor-setup-draft">{t("Draft", "초안")}</span>
          </header>

          <form className="investor-policy-form" onSubmit={(event) => { event.preventDefault(); setSubmitted(true); }}>
            <div className="investor-policy-form__grid">
              <label htmlFor="totalLimit">
                <span>{t("Total investment limit", "총 투자 한도")}</span>
                <div><input id="totalLimit" name="totalLimit" inputMode="numeric" defaultValue="50,000" /><small>USDC</small></div>
              </label>
              <label htmlFor="perInvoiceLimit">
                <span>{t("Maximum per invoice", "인보이스당 최대 금액")}</span>
                <div><input id="perInvoiceLimit" name="perInvoiceLimit" inputMode="numeric" defaultValue="20,000" /><small>USDC</small></div>
              </label>
              <label htmlFor="buyerAllowlist">
                <span>{t("Buyer allowlist", "구매기업 허용 목록")}</span>
                <div><input id="buyerAllowlist" name="buyerAllowlist" defaultValue="Prime Mobility" /></div>
              </label>
              <label htmlFor="minimumScore">
                <span>{t("Minimum Risk Score", "최소 위험 점수")}</span>
                <div><input id="minimumScore" name="minimumScore" inputMode="numeric" defaultValue="80" /><small>/ 100</small></div>
              </label>
              <label htmlFor="maximumTerm">
                <span>{t("Maximum remaining term", "최대 잔존 만기")}</span>
                <div><input id="maximumTerm" name="maximumTerm" inputMode="numeric" defaultValue="120" /><small>{t("days", "일")}</small></div>
              </label>
              <label htmlFor="policyTerm">
                <span>{t("Policy expiry", "정책 만료일")}</span>
                <div><input id="policyTerm" name="policyTerm" defaultValue="2026-12-31" /></div>
              </label>
            </div>

            <footer>
              <p>
                <Info size={15} weight="fill" aria-hidden="true" />
                {t(
                  "These settings are prepared locally and are not yet submitted to an investment API.",
                  "설정 값은 현재 화면에서만 준비되며 투자 API로 전송되지 않습니다.",
                )}
              </p>
              <button className="investor-primary-button" type="submit">
                <ShieldCheck size={15} weight="fill" aria-hidden="true" />
                {t("Save policy draft", "투자 정책 초안 저장")}
              </button>
            </footer>
          </form>

          {submitted && (
            <p className="investor-setup-success" role="status">
              <CheckCircle size={15} weight="fill" aria-hidden="true" />
              {t("Policy draft is ready for the future mandate API integration.", "투자 정책 초안이 준비되었습니다. 향후 위임 API와 연동됩니다.")}
            </p>
          )}
        </section>
      </div>
    </section>
  );
}
