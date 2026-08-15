import { BuildingOffice, CheckCircle } from "@phosphor-icons/react";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { useLanguage } from "../../i18n/LanguageContext";

export function InvestorProfilePage() {
  const { t } = useLanguage();

  return (
    <section className="company-wallet-page">
      <header className="page-heading">
        <div>
          <h1>{t("Profile", "Profile")}</h1>
          <p>{t("Review your investor company information and the external wallet used to sign policies and fund your Vault.", "투자자 기업 정보와 정책 서명 및 Vault 예치에 사용하는 외부 지갑을 확인하세요.")}</p>
        </div>
      </header>
      <div className="company-wallet-grid">
        <article className="profile-card">
          <header className="settings-card__header">
            <span className="settings-card__icon settings-card__icon--blue" aria-hidden="true"><BuildingOffice size={18} weight="fill" /></span>
            <div><h2>{t("Company Information", "기업 정보")}</h2><p>{t("Investor account profile", "투자자 계정 프로필")}</p></div>
            <span className="verification-pill"><CheckCircle size={13} weight="fill" aria-hidden="true" />{t("KYB verified", "KYB 인증 완료")}</span>
          </header>
          <dl className="company-details">
            <div><dt>{t("Legal company name", "기업명")}</dt><dd>Nova Capital</dd></div>
            <div><dt>{t("Account role", "기업 유형")}</dt><dd>{t("Investor", "Investor")}</dd></div>
            <div><dt>{t("Company email", "기업 이메일")}</dt><dd>investor@company.com</dd></div>
            <div><dt>{t("KYB status", "KYB 인증 상태")}</dt><dd className="verified-value">{t("Completed", "인증 완료")}</dd></div>
          </dl>
          <p className="wallet-connection-description">{t("Company information has been verified for this MVP account.", "기업 정보 확인이 완료된 MVP 계정입니다.")}</p>
        </article>
        <SolanaWalletConnection
          title={t("Wallet", "Wallet")}
          description={t("Connect an external Solana wallet to sign Investment Policy changes and deposit Devnet USDC into your Vault. InvoiceX never exposes or stores seed phrases or private keys.", "Investment Policy 변경 서명과 Vault Devnet USDC 예치를 위해 외부 Solana 지갑을 연결하세요. InvoiceX는 시드 문구나 개인키를 노출하거나 저장하지 않습니다.")}
        />
      </div>
    </section>
  );
}
