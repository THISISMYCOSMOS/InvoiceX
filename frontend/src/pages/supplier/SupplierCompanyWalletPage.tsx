import { BuildingOffice, CheckCircle, LinkSimple, PencilSimple, SignOut, Wallet } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { updateCompanyProfile } from "../../api/onboarding.api";
import { rwaApi, type SettlementWallet } from "../../api/rwa.api";
import { useCurrentPrivyAccount, useUpdateCurrentPrivyAccount } from "../../auth/currentAccount";
import { clearDemoSession, getDemoSession } from "../../auth/demoAccounts";
import { useSignupAuth } from "../../auth/SignupAuthContext";
import { useLanguage } from "../../i18n/LanguageContext";
import { useDevnetUsdcBalance } from "../../hooks/useDevnetUsdcBalance";

function formatKoreanBusinessRegistration(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 10);
  if (digits.length <= 3) return digits;
  if (digits.length <= 5) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, 5)}-${digits.slice(5)}`;
}

function displayKoreanBusinessRegistration(value: string) {
  const formatted = formatKoreanBusinessRegistration(value);
  return value.replace(/\D/g, "").length === 10 ? formatted : "등록번호 형식 오류";
}

function formatKoreanPhone(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 3) return digits;
  if (digits.length <= 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, digits.length - 4)}-${digits.slice(-4)}`;
}

type CompanyProfileForm = {
  companyName: string;
  registrationNumber: string;
  representativeName: string;
  representativeTitle: string;
  representativePhone: string;
};

const emptyProfileForm: CompanyProfileForm = {
  companyName: "",
  registrationNumber: "",
  representativeName: "",
  representativeTitle: "",
  representativePhone: "",
};

export function SupplierCompanyWalletPage() {
  const { t } = useLanguage();
  const currentAccount = useCurrentPrivyAccount();
  const updateCurrentAccount = useUpdateCurrentPrivyAccount();
  const { authenticated, getAccessToken, logout } = useSignupAuth();
  const navigate = useNavigate();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [settlementWallet, setSettlementWallet] = useState<SettlementWallet | null>(null);
  const [isExternalWalletConnectorOpen, setIsExternalWalletConnectorOpen] = useState(false);
  const [walletError, setWalletError] = useState<string | null>(null);
  const [isWithdrawing, setIsWithdrawing] = useState(false);
  const [withdrawalError, setWithdrawalError] = useState<string | null>(null);
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileForm, setProfileForm] = useState<CompanyProfileForm>(emptyProfileForm);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);
  const activeWalletAddress = settlementWallet?.address ?? currentAccount?.walletAddress ?? null;
  const activeWalletUsdcBalance = useDevnetUsdcBalance(activeWalletAddress);
  const displayedUsdcBalance = activeWalletUsdcBalance.balanceUsdc?.toLocaleString(undefined, {
    maximumFractionDigits: 6,
  });

  useEffect(() => {
    if (!currentAccount || isEditingProfile) return;
    setProfileForm({
      companyName: currentAccount.companyName,
      registrationNumber: formatKoreanBusinessRegistration(currentAccount.registrationNumber),
      representativeName: currentAccount.userName ?? "",
      representativeTitle: currentAccount.userTitle ?? "",
      representativePhone: formatKoreanPhone(currentAccount.userPhone ?? ""),
    });
  }, [currentAccount, isEditingProfile]);

  useEffect(() => {
    if (!currentAccount) return;
    let active = true;
    void rwaApi.getSettlementWallet()
      .then((savedWallet) => {
        if (!active) return;
        setSettlementWallet(savedWallet ?? {
          walletType: "EMBEDDED",
          address: currentAccount.walletAddress,
          embeddedWalletAddress: currentAccount.walletAddress,
        });
      })
      .catch(() => {
        if (active) setWalletError(t("Unable to load the settlement wallet.", "정산 지갑 정보를 불러오지 못했습니다."));
      });
    return () => {
      active = false;
    };
  }, [currentAccount, t]);

  const selectEmbeddedWallet = async () => {
    if (!currentAccount) return;
    setWalletError(null);
    try {
      const updated = await rwaApi.updateSettlementWallet("EMBEDDED");
      setSettlementWallet(updated ?? {
        walletType: "EMBEDDED",
        address: currentAccount.walletAddress,
        embeddedWalletAddress: currentAccount.walletAddress,
      });
      setIsExternalWalletConnectorOpen(false);
    } catch (error) {
      setWalletError(error instanceof Error ? error.message : t("Unable to update the settlement wallet.", "정산 지갑을 변경하지 못했습니다."));
    }
  };

  const connectExternalWallet = async (address: string) => {
    if (!currentAccount) return;
    setWalletError(null);
    const updated = await rwaApi.updateSettlementWallet("EXTERNAL", address);
    setSettlementWallet(updated ?? {
      walletType: "EXTERNAL",
      address,
      embeddedWalletAddress: currentAccount.walletAddress,
    });
    setIsExternalWalletConnectorOpen(false);
  };

  const startProfileEdit = () => {
    if (!currentAccount) return;
    setProfileForm({
      companyName: currentAccount.companyName,
      registrationNumber: formatKoreanBusinessRegistration(currentAccount.registrationNumber),
      representativeName: currentAccount.userName ?? "",
      representativeTitle: currentAccount.userTitle ?? "",
      representativePhone: formatKoreanPhone(currentAccount.userPhone ?? ""),
    });
    setProfileError(null);
    setProfileSuccess(null);
    setIsEditingProfile(true);
  };

  const handleSaveProfile = async () => {
    if (!currentAccount) return;
    if (profileForm.registrationNumber.replace(/\D/g, "").length !== 10) {
      setProfileError(t("Enter a 10-digit Korean business registration number.", "사업자등록번호 숫자 10자리를 입력해 주세요."));
      return;
    }
    setIsSavingProfile(true);
    setProfileError(null);
    setProfileSuccess(null);
    try {
      const token = getDemoSession()?.accessToken ?? await getAccessToken();
      if (!token) throw new Error(t("Your login session is unavailable.", "로그인 세션을 확인할 수 없습니다."));
      const updated = await updateCompanyProfile(token, {
        company: {
          name: profileForm.companyName,
          type: currentAccount.role,
          countryCode: currentAccount.countryCode,
          registrationNumber: profileForm.registrationNumber,
        },
        representative: {
          name: profileForm.representativeName,
          title: profileForm.representativeTitle,
          phone: profileForm.representativePhone,
        },
      });
      if (!updated.company) {
        throw new Error(t("The updated company profile was not returned.", "수정된 회사 정보를 확인할 수 없습니다."));
      }
      updateCurrentAccount({
        companyName: updated.company.name,
        registrationNumber: updated.company.registrationNumber,
        userName: updated.user.name,
        userPhone: updated.user.phone,
        userTitle: updated.user.title,
      });
      setIsEditingProfile(false);
      setProfileSuccess(t("Company information has been saved.", "회사 정보가 저장되었습니다."));
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : t("Unable to save company information.", "회사 정보를 저장하지 못했습니다."));
    } finally {
      setIsSavingProfile(false);
    }
  };

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
      setWithdrawalError(error instanceof Error ? error.message : t("Unable to withdraw this account.", "계정을 탈퇴하지 못했습니다."));
    } finally {
      setIsWithdrawing(false);
    }
  };

  return (
    <section className="company-wallet-page">
      <header className="page-heading">
        <div>
          <h1>{t("Company & Wallet", "회사 및 지갑")}</h1>
          <p>
            {t(
              "Review your verified company profile and manage the wallet used for early settlement.",
              "인증된 회사 정보를 확인하고 조기정산에 사용할 지갑을 관리하세요.",
            )}
          </p>
        </div>
      </header>

      <div className="company-wallet-grid">
        <article className="profile-card">
          <header className="settings-card__header">
            <span className="settings-card__icon settings-card__icon--blue" aria-hidden="true">
              <BuildingOffice size={18} weight="fill" />
            </span>
            <div>
              <h2>{t("Company information", "회사 정보")}</h2>
              <p>{t("Verified supplier profile", "인증된 공급기업 프로필")}</p>
            </div>
            <div className="company-profile-header-actions">
              {currentAccount && !isEditingProfile ? (
                <button className="company-profile-edit-button" type="button" onClick={startProfileEdit}>
                  <PencilSimple size={14} weight="bold" aria-hidden="true" />
                  {t("Edit", "정보 수정")}
                </button>
              ) : null}
              <span className="verification-pill">
                <CheckCircle size={13} weight="fill" aria-hidden="true" />
                {t("Verified", "인증 완료")}
              </span>
            </div>
          </header>

          {isEditingProfile ? (
            <form className="company-profile-form" onSubmit={(event) => { event.preventDefault(); void handleSaveProfile(); }}>
              <label className="company-profile-field">
                <span>{t("Legal company name", "법인명")}</span>
                <input aria-label={t("Legal company name", "법인명")} value={profileForm.companyName} maxLength={200} onChange={(event) => setProfileForm((current) => ({ ...current, companyName: event.target.value }))} required />
              </label>
              <label className="company-profile-field">
                <span>{t("Country code", "국가 코드")}</span>
                <input value={currentAccount?.countryCode ?? "KR"} readOnly aria-readonly="true" />
              </label>
              <label className="company-profile-field">
                <span>{t("Company registration number", "기업 등록번호")}</span>
                <input aria-label={t("Company registration number", "기업 등록번호")} inputMode="numeric" maxLength={12} value={profileForm.registrationNumber} onChange={(event) => setProfileForm((current) => ({ ...current, registrationNumber: formatKoreanBusinessRegistration(event.target.value) }))} placeholder="123-45-67890" required />
              </label>
              <label className="company-profile-field">
                <span>{t("Representative", "대표자")}</span>
                <input aria-label={t("Representative", "대표자")} value={profileForm.representativeName} maxLength={100} onChange={(event) => setProfileForm((current) => ({ ...current, representativeName: event.target.value }))} required />
              </label>
              <label className="company-profile-field">
                <span>{t("Representative title", "대표자 직책")}</span>
                <input aria-label={t("Representative title", "대표자 직책")} value={profileForm.representativeTitle} maxLength={100} onChange={(event) => setProfileForm((current) => ({ ...current, representativeTitle: event.target.value }))} required />
              </label>
              <label className="company-profile-field">
                <span>{t("Contact number", "담당자 연락처")}</span>
                <input aria-label={t("Contact number", "담당자 연락처")} inputMode="tel" maxLength={13} value={profileForm.representativePhone} onChange={(event) => setProfileForm((current) => ({ ...current, representativePhone: formatKoreanPhone(event.target.value) }))} placeholder="010-1234-5678" required />
              </label>
              <div className="company-profile-readonly" aria-label={t("Uneditable account information", "변경할 수 없는 계정 정보")}>
                <span>{t("Company email", "회사 이메일")} <strong>{currentAccount?.userEmail}</strong></span>
                <span>{t("Account role", "계정 역할")} <strong>{t("Supplier", "공급기업")}</strong></span>
              </div>
              {profileError ? <p className="company-profile-message is-error" role="alert">{profileError}</p> : null}
              <div className="company-profile-form-actions">
                <button className="secondary-button" type="button" onClick={() => { setIsEditingProfile(false); setProfileError(null); }} disabled={isSavingProfile}>{t("Cancel", "취소")}</button>
                <button className="primary-button" type="submit" disabled={isSavingProfile}>{isSavingProfile ? t("Saving...", "저장 중...") : t("Save changes", "변경사항 저장")}</button>
              </div>
            </form>
          ) : (
            <dl className="company-details">
              <div><dt>{t("Legal company name", "법인명")}</dt><dd>{currentAccount?.companyName ?? "Alpha Components Co., Ltd."}</dd></div>
              <div><dt>{t("Country code", "국가 코드")}</dt><dd>{currentAccount?.countryCode ?? "KR"}</dd></div>
              <div><dt>{t("Company registration number", "기업 등록번호")}</dt><dd>{displayKoreanBusinessRegistration(currentAccount?.registrationNumber ?? "1234567890")}</dd></div>
              <div><dt>{t("Representative", "대표자")}</dt><dd>{currentAccount?.userName ?? t("Minjun Kim", "김민준")}</dd></div>
              <div><dt>{t("Representative title", "대표자 직책")}</dt><dd>{currentAccount?.userTitle ?? "—"}</dd></div>
              <div><dt>{t("Contact number", "담당자 연락처")}</dt><dd>{currentAccount?.userPhone ?? "—"}</dd></div>
              <div><dt>{t("Company email", "회사 이메일")}</dt><dd>{currentAccount?.userEmail ?? "finance@alphacomponents.com"}</dd></div>
              <div><dt>{t("Account role", "계정 역할")}</dt><dd>{t("Supplier", "공급기업")}</dd></div>
              <div><dt>{t("Verification status", "기업 인증 상태")}</dt><dd className="verified-value">{t("Completed", "인증 완료")}</dd></div>
            </dl>
          )}
          {profileSuccess ? <p className="company-profile-message is-success" role="status"><CheckCircle size={14} weight="fill" aria-hidden="true" />{profileSuccess}</p> : null}
        </article>

        {currentAccount ? (
          <article className="wallet-card">
            <header className="settings-card__header">
              <span className="settings-card__icon settings-card__icon--navy" aria-hidden="true">
                <Wallet size={18} weight="fill" />
              </span>
              <div>
                <h2>{settlementWallet?.walletType === "EXTERNAL" ? t("External settlement wallet", "외부 정산 지갑") : t("Embedded settlement wallet", "임베디드 정산 지갑")}</h2>
                <p>{settlementWallet?.walletType === "EXTERNAL" ? t("Connected with your Solana wallet", "연결한 Solana 지갑으로 정산") : t("User-owned wallet provisioned by Privy", "Privy가 생성한 사용자 소유 지갑")}</p>
              </div>
              <span className="wallet-status is-connected"><span />{t("Active", "사용 중")}</span>
            </header>
            <div className="wallet-address-panel">
              <div>
                <span>{t("Solana wallet address", "Solana 지갑 주소")}</span>
                <strong>{settlementWallet?.address ?? currentAccount.walletAddress}</strong>
              </div>
            </div>
            <div className="wallet-metrics">
              <div>
                <span>{t("Available balance", "사용 가능 잔액")}</span>
                <strong>
                  {activeWalletUsdcBalance.isLoading
                    ? t("Loading", "조회 중")
                    : activeWalletUsdcBalance.isError
                      ? t("Unavailable", "조회 실패")
                      : displayedUsdcBalance ?? "—"} <small>USDC</small>
                </strong>
              </div>
              <div>
                <span>{t("Network", "네트워크")}</span>
                <strong>Solana Devnet</strong>
              </div>
              <div>
                <span>{t("Wallet type", "지갑 유형")}</span>
                <strong>{settlementWallet?.walletType === "EXTERNAL" ? t("External", "외부 지갑") : t("Embedded", "임베디드")}</strong>
              </div>
            </div>
            <footer className="wallet-card__footer">
              <p>
                <CheckCircle size={15} weight="fill" aria-hidden="true" />
                {settlementWallet?.walletType === "EXTERNAL"
                  ? t("Early-settlement USDC will be sent to this external wallet.", "조기정산 USDC가 이 외부 지갑으로 지급됩니다.")
                  : t("This address is loaded from the authenticated company account.", "인증된 회사 계정에 연결된 주소입니다.")}
              </p>
              {settlementWallet?.walletType === "EXTERNAL" ? (
                <button className="secondary-button wallet-action" type="button" onClick={() => void selectEmbeddedWallet()}>
                  {t("Disconnect external wallet", "외부 지갑 연결 해제")}
                </button>
              ) : (
                <button className="secondary-button wallet-action" type="button" onClick={() => setIsExternalWalletConnectorOpen((open) => !open)}>
                  <LinkSimple size={14} weight="bold" aria-hidden="true" />
                  {t("Connect external wallet", "외부 지갑 연결")}
                </button>
              )}
            </footer>
            {walletError ? <p className="wallet-error" role="alert">{walletError}</p> : null}
          </article>
        ) : (
          <SolanaWalletConnection
            title={t("Settlement wallet", "정산 지갑")}
            description={t(
              "Early-settlement funds will be paid in USDC to the connected Solana wallet.",
              "조기정산 금액은 연결된 Solana 지갑으로 USDC 지급됩니다.",
            )}
            onWalletConnected={(address) => rwaApi.saveSupplierWallet(address)}
            onWalletDisconnected={() => undefined}
          />
        )}
      </div>

      {currentAccount && isExternalWalletConnectorOpen ? (
        <section className="wallet-external-connector" aria-label={t("Connect external wallet", "외부 지갑 연결")}>
          <SolanaWalletConnection
            title={t("Connect an external settlement wallet", "외부 정산 지갑 연결")}
            description={t(
              "Connect Phantom, Solflare, or another Solana wallet to receive early-settlement USDC.",
              "Phantom, Solflare 등 Solana 지갑을 연결하면 조기정산 USDC를 해당 지갑으로 받을 수 있습니다.",
            )}
            onWalletConnected={connectExternalWallet}
            onWalletDisconnected={() => {
              if (settlementWallet?.walletType === "EXTERNAL") void selectEmbeddedWallet();
            }}
          />
        </section>
      ) : null}

      <section className="profile-logout" aria-labelledby="profile-logout-title">
        <div>
          <h2 id="profile-logout-title">{t("Sign out", "로그아웃")}</h2>
          <p>{t("End this session on the current device.", "현재 기기에서 안전하게 로그아웃합니다.")}</p>
        </div>
        <button className="profile-logout__button" type="button" onClick={() => void handleLogout()} disabled={isLoggingOut}>
          <SignOut size={16} weight="bold" aria-hidden="true" />
          {isLoggingOut ? t("Signing out...", "로그아웃 중...") : t("Sign out", "로그아웃")}
        </button>
      </section>

      <section className="profile-withdrawal" aria-labelledby="profile-withdrawal-title">
        <div>
          <h2 id="profile-withdrawal-title">{t("Delete account", "계정 탈퇴")}</h2>
          <p>
            {t(
              "InvoiceX access and the saved settlement-wallet preference will be removed immediately.",
              "InvoiceX 접근 권한과 저장된 정산 지갑 설정이 즉시 해제됩니다.",
            )}
          </p>
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
