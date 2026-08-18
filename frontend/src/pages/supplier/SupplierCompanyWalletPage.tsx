import { BuildingOffice, CheckCircle, Wallet } from "@phosphor-icons/react";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { rwaApi } from "../../api/rwa.api";
import { useCurrentPrivyAccount } from "../../auth/currentAccount";
import { useLanguage } from "../../i18n/LanguageContext";

export function SupplierCompanyWalletPage() {
  const { t } = useLanguage();
  const currentAccount = useCurrentPrivyAccount();

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
            <span className="verification-pill">
              <CheckCircle size={13} weight="fill" aria-hidden="true" />
              {t("Verified", "인증 완료")}
            </span>
          </header>

          <dl className="company-details">
            <div>
              <dt>{t("Legal company name", "법인명")}</dt>
              <dd>{currentAccount?.companyName ?? "Alpha Components Co., Ltd."}</dd>
            </div>
            <div>
              <dt>{t("Business registration number", "사업자등록번호")}</dt>
              <dd>{currentAccount?.businessRegistrationNumber ?? "123-45-67890"}</dd>
            </div>
            <div>
              <dt>{t("Representative", "대표자")}</dt>
              <dd>{currentAccount?.userName ?? t("Minjun Kim", "김민준")}</dd>
            </div>
            <div>
              <dt>{t("Company email", "회사 이메일")}</dt>
              <dd>{currentAccount?.userEmail ?? "finance@alphacomponents.com"}</dd>
            </div>
            <div>
              <dt>{t("Account role", "계정 역할")}</dt>
              <dd>{t("Supplier", "공급기업")}</dd>
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
              <span className="settings-card__icon settings-card__icon--navy" aria-hidden="true">
                <Wallet size={18} weight="fill" />
              </span>
              <div>
                <h2>{t("Embedded settlement wallet", "임베디드 정산 지갑")}</h2>
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
            <footer className="wallet-card__footer">
              <p>
                <CheckCircle size={15} weight="fill" aria-hidden="true" />
                {t(
                  "This address is loaded from the authenticated company account.",
                  "인증된 회사 계정에 연결된 주소입니다.",
                )}
              </p>
            </footer>
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

      <aside className="wallet-security-note">
        <CheckCircle size={17} weight="fill" aria-hidden="true" />
        <div>
          <strong>{t("Wallet security", "지갑 보안")}</strong>
          <p>
            {currentAccount
              ? t(
                  "InvoiceX stores only the public wallet address linked to your account. Private keys remain under the user's Privy wallet control.",
                  "InvoiceX는 계정에 연결된 공개 지갑 주소만 저장하며, 개인키는 사용자의 Privy 지갑 통제 아래 유지됩니다.",
                )
              : t(
                  "InvoiceX never stores private keys. The connected address is not saved until a separate settlement API is integrated.",
                  "InvoiceX는 개인키를 저장하지 않으며, 별도 정산 API가 연동되기 전까지 연결된 주소도 저장하지 않습니다.",
                )}
          </p>
        </div>
      </aside>
    </section>
  );
}
