import { CheckCircle, CircleNotch, Vault } from "@phosphor-icons/react";
import { VersionedTransaction } from "@solana/web3.js";
import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { rwaApi, type VaultBalance } from "../../api/rwa.api";
import { useCurrentPrivyAccount } from "../../auth/currentAccount";
import { useSignupAuth } from "../../auth/SignupAuthContext";
import { useDevnetUsdcBalance } from "../../hooks/useDevnetUsdcBalance";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";
import { useLanguage } from "../../i18n/LanguageContext";

type VaultDepositPhase = "IDLE" | "PREPARING" | "AWAITING_SIGNATURE" | "CONFIRMING" | "CONFIRMED" | "FAILED";

function parseAmount(value: string): number {
  return Number(value.replace(/[^\d]/g, ""));
}

function fromBase64(value: string): Uint8Array {
  return Uint8Array.from(window.atob(value), (character) => character.charCodeAt(0));
}

function toBase64(value: Uint8Array): string {
  let binary = "";
  value.forEach((byte) => { binary += String.fromCharCode(byte); });
  return window.btoa(binary);
}

export function InvestorVaultPage() {
  const { t } = useLanguage();
  const { connection } = useConnection();
  const { connected, publicKey, signTransaction, sendTransaction } = useWallet();
  const {
    authenticated,
    embeddedSolanaWalletReady,
    hasEmbeddedSolanaWallet,
    signEmbeddedSolanaTransaction,
  } = useSignupAuth();
  const currentAccount = useCurrentPrivyAccount();
  const embeddedWalletAddress = currentAccount?.walletAddress ?? null;
  const connectedWalletAddress = publicKey?.toBase58() ?? embeddedWalletAddress;
  const canUseExternalWallet = Boolean(connected && publicKey && sendTransaction);
  const canUseEmbeddedWallet = Boolean(
    authenticated
      && embeddedSolanaWalletReady
      && embeddedWalletAddress
      && hasEmbeddedSolanaWallet(embeddedWalletAddress),
  );
  const canDeposit = canUseExternalWallet || canUseEmbeddedWallet;
  const walletUsdcBalance = useDevnetUsdcBalance(connectedWalletAddress);
  const dashboard = useInvestorDashboard();
  const [depositAmount, setDepositAmount] = useState("1");
  const [vault, setVault] = useState<VaultBalance | null>(null);
  const [isVaultLoading, setIsVaultLoading] = useState(false);
  const [vaultLoadFailed, setVaultLoadFailed] = useState(false);
  const [isDepositing, setIsDepositing] = useState(false);
  const [phase, setPhase] = useState<VaultDepositPhase>("IDLE");
  const [signature, setSignature] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!connectedWalletAddress) {
      setVault(null);
      setVaultLoadFailed(false);
      return;
    }
    let cancelled = false;
    setIsVaultLoading(true);
    setVaultLoadFailed(false);
    void rwaApi.getVault(connectedWalletAddress)
      .then((nextVault) => { if (!cancelled) setVault(nextVault); })
      .catch(() => { if (!cancelled) setVaultLoadFailed(true); })
      .finally(() => { if (!cancelled) setIsVaultLoading(false); });
    return () => { cancelled = true; };
  }, [connectedWalletAddress]);

  const depositToVault = async () => {
    if (!connectedWalletAddress || !canDeposit) {
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
    setPhase("PREPARING");
    setSignature(null);
    try {
      const ownerWalletAddress = connectedWalletAddress;
      const prepared = await rwaApi.prepareVaultDeposit(ownerWalletAddress, amountUsdc);
      const transaction = VersionedTransaction.deserialize(fromBase64(prepared.transactionBase64));
      setPhase("AWAITING_SIGNATURE");
      let nextVault: VaultBalance;
      if (canUseExternalWallet && publicKey && sendTransaction) {
        if (prepared.sponsored) {
          if (!signTransaction || !prepared.sponsorDepositId) {
            throw new Error(t("This wallet does not support gasless transaction signing.", "이 지갑은 가스리스 트랜잭션 서명을 지원하지 않습니다."));
          }
          const signedTransaction = await signTransaction(transaction);
          setPhase("CONFIRMING");
          nextVault = await rwaApi.sponsorVaultDeposit(ownerWalletAddress, prepared.sponsorDepositId, toBase64(signedTransaction.serialize()));
        } else {
          const transactionSignature = await sendTransaction(transaction, connection, { preflightCommitment: "confirmed" });
          setSignature(transactionSignature);
          setPhase("CONFIRMING");
          await connection.confirmTransaction(transactionSignature, "confirmed");
          nextVault = await rwaApi.confirmVaultDeposit(ownerWalletAddress, amountUsdc, transactionSignature);
        }
      } else {
        const signedTransaction = await signEmbeddedSolanaTransaction(ownerWalletAddress, transaction.serialize());
        if (prepared.sponsored) {
          if (!prepared.sponsorDepositId) {
            throw new Error(t("This wallet does not support gasless transaction signing.", "이 지갑은 가스리스 트랜잭션 서명을 지원하지 않습니다."));
          }
          setPhase("CONFIRMING");
          nextVault = await rwaApi.sponsorVaultDeposit(ownerWalletAddress, prepared.sponsorDepositId, toBase64(signedTransaction));
        } else {
          const transactionSignature = await connection.sendRawTransaction(signedTransaction, { preflightCommitment: "confirmed" });
          setSignature(transactionSignature);
          setPhase("CONFIRMING");
          await connection.confirmTransaction(transactionSignature, "confirmed");
          nextVault = await rwaApi.confirmVaultDeposit(ownerWalletAddress, amountUsdc, transactionSignature);
        }
      }
      setVault(nextVault);
      void walletUsdcBalance.refresh();
      setPhase("CONFIRMED");
      setSuccess(t("The deposit was confirmed. Treasury Agent can evaluate eligible RWAs automatically.", "예치가 확인되었습니다. Treasury Agent가 적격 RWA를 자동 평가할 수 있습니다."));
    } catch (cause) {
      setPhase("FAILED");
      setError(cause instanceof Error ? cause.message : t("Vault deposit failed.", "Vault 예치에 실패했습니다."));
    } finally {
      setIsDepositing(false);
    }
  };

  const availableUsdc = vault?.availableUsdc ?? dashboard.data?.availableVaultUsdc ?? 0;
  const investedUsdc = dashboard.data?.outstandingPrincipalUsdc ?? 0;
  const totalUsdc = availableUsdc + investedUsdc;
  const vaultValue = (value: number) => isVaultLoading ? t("Loading", "조회 중") : vaultLoadFailed ? t("Unavailable", "조회 실패") : `${value.toLocaleString()} USDC`;
  const phaseLabel: Record<VaultDepositPhase, string> = {
    IDLE: t("Ready for deposit", "예치 준비"),
    PREPARING: t("Preparing transaction", "트랜잭션 준비 중"),
    AWAITING_SIGNATURE: t("Waiting for wallet signature", "지갑 서명 대기 중"),
    CONFIRMING: t("Confirming on Devnet", "Devnet 확인 중"),
    CONFIRMED: t("Deposit confirmed", "예치 확인 완료"),
    FAILED: t("Deposit needs attention", "예치 확인 필요"),
  };

  return (
    <section className="investor-setup-page">
      <header className="investor-page-heading investor-setup-heading">
        <div>
          <p className="investor-breadcrumb">{t("Investor / Vault", "투자자 / Vault")}</p>
          <h1>Vault</h1>
          <p>{t("Manage the USDC capital Treasury Agent can use for automatic investments.", "Treasury Agent의 자동 투자에 사용할 USDC 자금을 관리하세요.")}</p>
        </div>
      </header>
      <div className="investor-setup-stack">
        <section className="investor-setup-policy-card investor-vault-deposit-card">
          <header>
            <span className="investor-setup-icon" aria-hidden="true"><Vault size={18} weight="bold" /></span>
            <div><h2>{t("Vault balance", "Vault 잔액")}</h2><p>{t("Only available Vault funds may be used for new investments.", "Vault 가용 잔액만 신규 투자에 사용할 수 있습니다.")}</p></div>
          </header>
          <div className="investor-vault-deposit-card__body">
            <dl className="investor-vault-balance-summary">
              <div><dt>{t("Total Balance", "총 잔액")}</dt><dd>{vaultValue(totalUsdc)}</dd><small>{t("Available balance plus current investments", "가용 잔액과 현재 투자금의 합계")}</small></div>
              <div><dt>{t("Available Balance", "투자 가능 금액")}</dt><dd>{vaultValue(availableUsdc)}</dd><small>{t("Available for Treasury Agent purchases", "Treasury Agent 자동 매수에 사용 가능")}</small></div>
              <div><dt>{t("Invested Amount", "현재 투자 중 금액")}</dt><dd>{investedUsdc.toLocaleString()} USDC</dd><small>{t("Outstanding investment principal", "미상환 투자 원금")}</small></div>
              <div><dt>{t("Connected wallet balance", "연결 지갑 잔액")}</dt><dd>{walletUsdcBalance.isLoading ? t("Loading", "조회 중") : walletUsdcBalance.isError ? t("Unavailable", "조회 실패") : `${(walletUsdcBalance.balanceUsdc ?? 0).toLocaleString()} USDC`}</dd><small>{t("Devnet USDC available to deposit", "예치 가능한 Devnet USDC")}</small></div>
            </dl>
            {!connected && !embeddedWalletAddress ? <p className="wallet-error"><Link to="/investor/profile">{t("Connect a Solana wallet in Profile before depositing.", "예치 전 Profile에서 Solana 지갑을 연결해 주세요.")}</Link></p> : null}
            <div className="investor-vault-deposit-form">
              <label htmlFor="vaultDeposit"><span>{t("Deposit amount", "예치 금액")}</span><div><input id="vaultDeposit" inputMode="numeric" value={depositAmount} onChange={(event) => setDepositAmount(event.target.value)} /><small>USDC</small></div></label>
              <button className="investor-primary-button" type="button" disabled={!canDeposit || isDepositing} onClick={() => void depositToVault()}><Vault size={15} weight="fill" aria-hidden="true" />{isDepositing ? phaseLabel[phase] : t("Deposit USDC", "USDC 예치")}</button>
            </div>
          </div>
          <div className="investor-vault-progress" role="status" aria-live="polite">
            <div className="investor-vault-progress__status">{phase === "PREPARING" || phase === "CONFIRMING" ? <CircleNotch size={15} weight="bold" className="investor-vault-progress__spin" aria-hidden="true" /> : <Vault size={15} weight="fill" aria-hidden="true" />}<span>{phaseLabel[phase]}</span></div>
            {(vault?.vaultAddress || signature) ? <dl>{vault?.vaultAddress ? <div><dt>{t("Vault address", "Vault 주소")}</dt><dd>{`${vault.vaultAddress.slice(0, 8)}...${vault.vaultAddress.slice(-6)}`}</dd></div> : null}{signature ? <div><dt>{t("Deposit signature", "예치 서명")}</dt><dd>{`${signature.slice(0, 8)}...${signature.slice(-6)}`}</dd></div> : null}</dl> : null}
          </div>
        </section>
        {success ? <p className="investor-setup-success" role="status"><CheckCircle size={15} weight="fill" aria-hidden="true" />{success}</p> : null}
        {error ? <p className="wallet-error" role="alert">{error}</p> : null}
      </div>
    </section>
  );
}
