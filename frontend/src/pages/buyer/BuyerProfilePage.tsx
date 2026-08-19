import { BuildingOffice, CheckCircle, LinkSimple, SignOut, Wallet } from "@phosphor-icons/react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { rwaApi } from "../../api/rwa.api";
import { useCurrentPrivyAccount } from "../../auth/currentAccount";
import { clearDemoSession } from "../../auth/demoAccounts";
import { useSignupAuth } from "../../auth/SignupAuthContext";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { useDevnetUsdcBalance } from "../../hooks/useDevnetUsdcBalance";
import { useLanguage } from "../../i18n/LanguageContext";

function formatUsEin(value: string) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 9) return value;
  return `${digits.slice(0, 2)}-${digits.slice(2)}`;
}

export function BuyerProfilePage() {
  const { t } = useLanguage();
  const currentAccount = useCurrentPrivyAccount();
  const { authenticated, logout } = useSignupAuth();
  const navigate = useNavigate();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [isWithdrawing, setIsWithdrawing] = useState(false);
  const [withdrawalError, setWithdrawalError] = useState<string | null>(null);
  const [isExternalWalletConnectorOpen, setIsExternalWalletConnectorOpen] = useState(false);
  const embeddedWalletBalance = useDevnetUsdcBalance(currentAccount?.walletAddress ?? null);
  const displayedUsdcBalance = embeddedWalletBalance.balanceUsdc?.toLocaleString(undefined, {
    maximumFractionDigits: 6,
  });

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      clearDemoSession();
      if (authenticated) await logout();
      navigate("/login", { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleWithdrawAccount = async () => {
    setIsWithdrawing(true);
    setWithdrawalError(null);
    try {
      await rwaApi.withdrawAccount();
      clearDemoSession();
      if (authenticated) await logout();
      navigate("/login", { replace: true });
    } catch (error) {
      setWithdrawalError(error instanceof Error
        ? error.message
        : t("Unable to delete this account.", "계정을 탈퇴하지 못했습니다."));
    } finally {
      setIsWithdrawing(false);
    }
  };

  return (
    <section className="company-wallet-page buyer-profile-page">
      <header className="page-heading">
        <div>
          <h1>{t("Company profile", "기업 프로필")}</h1>
          <p>{t(
            "Review your company information and the wallets used to settle invoices in USDC.",
            "구매기업 정보와 인보이스 만기 정산에 사용하는 USDC 지갑을 확인하세요.",
          )}</p>
        </div>
      </header>

      <div className="company-wallet-grid">
        <article className="profile-card">
          <header className="settings-card__header">
            <span className="settings-card__icon settings-card__icon--green" aria-hidden="true">
              <BuildingOffice size={18} weight="fill" />
            </span>
            <div>
              <h2>{t("Company information", "회사 정보")}</h2>
              <p>{t("Verified buyer profile", "인증된 구매기업 프로필")}</p>
            </div>
            <span className="verification-pill">
              <CheckCircle size={13} weight="fill" aria-hidden="true" />
              {t("Verified", "인증 완료")}
            </span>
          </header>

          <dl className="company-details">
            <div>
              <dt>{t("Legal company name", "법인명")}</dt>
              <dd>{currentAccount?.companyName ?? "Halcyon Robotics Ltd"}</dd>
            </div>
            <div>
              <dt>{t("Country code", "국가 코드")}</dt>
              <dd>{currentAccount?.countryCode ?? "US"}</dd>
            </div>
            <div>
              <dt>{t("Employer Identification Number", "미국 EIN")}</dt>
              <dd>{formatUsEin(currentAccount?.registrationNumber ?? "123456789")}</dd>
            </div>
            <div>
              <dt>{t("Representative", "담당자")}</dt>
              <dd>{currentAccount?.userName ?? "—"}</dd>
            </div>
            <div>
              <dt>{t("Company email", "회사 이메일")}</dt>
              <dd>{currentAccount?.userEmail ?? "—"}</dd>
            </div>
            <div>
              <dt>{t("Account role", "계정 역할")}</dt>
              <dd>{t("Buyer", "구매기업")}</dd>
            </div>
            <div>
              <dt>{t("Settlement currency", "정산 통화")}</dt>
              <dd>USDC</dd>
            </div>
            <div>
              <dt>{t("Verification status", "기업 인증 상태")}</dt>
              <dd className="verified-value">{t("Completed", "인증 완료")}</dd>
            </div>
          </dl>
        </article>

        {currentAccount ? (
          <article className="wallet-card">
            <header className="settings-card__header">
              <span className="settings-card__icon settings-card__icon--green" aria-hidden="true">
                <Wallet size={18} weight="fill" />
              </span>
              <div>
                <h2>{t("Embedded wallet", "임베디드 지갑")}</h2>
                <p>{t("User-owned wallet provisioned by Privy", "Privy가 생성한 사용자 소유 지갑")}</p>
              </div>
              <span className="wallet-status is-connected"><span />{t("Active", "사용 중")}</span>
            </header>
            <div className="wallet-address-panel">
              <div>
                <span>{t("Solana wallet address", "Solana 지갑 주소")}</span>
                <strong>{currentAccount.walletAddress}</strong>
              </div>
            </div>
            <div className="wallet-metrics">
              <div>
                <span>{t("Available balance", "사용 가능 잔액")}</span>
                <strong>
                  {embeddedWalletBalance.isLoading
                    ? t("Loading", "조회 중")
                    : embeddedWalletBalance.isError
                      ? t("Unavailable", "조회 실패")
                      : displayedUsdcBalance ?? "—"} <small>USDC</small>
                </strong>
              </div>
              <div><span>{t("Network", "네트워크")}</span><strong>Solana Devnet</strong></div>
              <div><span>{t("Wallet type", "지갑 유형")}</span><strong>{t("Embedded", "임베디드")}</strong></div>
            </div>
            <footer className="wallet-card__footer">
              <p>
                <CheckCircle size={15} weight="fill" aria-hidden="true" />
                {t(
                  "This wallet was provisioned during signup and receives USDC invoice settlements.",
                  "가입 시 생성되어 인보이스 만기 USDC 정산을 수령하는 기본 지갑입니다.",
                )}
              </p>
              <button
                className="secondary-button wallet-action"
                type="button"
                onClick={() => setIsExternalWalletConnectorOpen((open) => !open)}
              >
                <LinkSimple size={14} weight="bold" aria-hidden="true" />
                {isExternalWalletConnectorOpen
                  ? t("Hide external wallet", "외부 지갑 닫기")
                  : t("Connect external wallet", "외부 지갑 연결")}
              </button>
            </footer>
          </article>
        ) : null}
      </div>

      {currentAccount && isExternalWalletConnectorOpen ? (
        <section className="wallet-external-connector" aria-label={t("External settlement wallet", "외부 정산 지갑")}>
          <SolanaWalletConnection
            title={t("External settlement wallet", "외부 정산 지갑")}
            description={t(
              "Connect a Solana wallet if you want to receive USDC invoice settlements in an external wallet.",
              "외부 지갑으로 인보이스 만기 USDC 정산을 수령하려면 Solana 지갑을 연결하세요.",
            )}
          />
        </section>
      ) : null}

      <section className="profile-logout" aria-labelledby="buyer-profile-logout-title">
        <div>
          <h2 id="buyer-profile-logout-title">{t("Sign out", "로그아웃")}</h2>
          <p>{t("End this session on the current device.", "현재 기기에서 안전하게 로그아웃합니다.")}</p>
        </div>
        <button className="profile-logout__button" type="button" onClick={() => void handleLogout()} disabled={isLoggingOut}>
          <SignOut size={16} weight="bold" aria-hidden="true" />
          {isLoggingOut ? t("Signing out...", "로그아웃 중...") : t("Sign out", "로그아웃")}
        </button>
      </section>

      <section className="profile-withdrawal" aria-labelledby="buyer-profile-withdrawal-title">
        <div>
          <h2 id="buyer-profile-withdrawal-title">{t("Delete account", "계정 탈퇴")}</h2>
          <p>{t(
            "Your InvoiceX account and saved company profile will be removed immediately.",
            "InvoiceX 계정과 저장된 구매기업 정보가 즉시 삭제됩니다.",
          )}</p>
        </div>
        <div className="profile-withdrawal__actions">
          {withdrawalError ? <p className="profile-withdrawal__error" role="alert">{withdrawalError}</p> : null}
          <button type="button" className="profile-withdrawal__button" onClick={() => void handleWithdrawAccount()} disabled={isWithdrawing}>
            {isWithdrawing ? t("Deleting account...", "탈퇴 처리 중...") : t("Delete account", "계정 탈퇴")}
          </button>
        </div>
      </section>
    </section>
  );
}
