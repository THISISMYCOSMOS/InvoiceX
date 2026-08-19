import { BuildingOffice, CheckCircle, SignOut } from "@phosphor-icons/react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { rwaApi } from "../../api/rwa.api";
import { useCurrentPrivyAccount } from "../../auth/currentAccount";
import { clearDemoSession } from "../../auth/demoAccounts";
import { useSignupAuth } from "../../auth/SignupAuthContext";
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
            "Review the company information used for invoice verification and USD payments.",
            "인보이스 확인 및 USD 지급에 사용하는 구매기업 정보를 확인하세요.",
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
              <dt>{t("Payment currency", "지급 통화")}</dt>
              <dd>USD</dd>
            </div>
            <div>
              <dt>{t("Verification status", "기업 인증 상태")}</dt>
              <dd className="verified-value">{t("Completed", "인증 완료")}</dd>
            </div>
          </dl>
        </article>
      </div>

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
