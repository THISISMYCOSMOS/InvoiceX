import { BuildingOffice, CheckCircle } from "@phosphor-icons/react";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { SolanaWalletConnection } from "../../components/SolanaWalletConnection";
import { useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";
import { DEMO_SUPPLIER_PROFILE } from "../../mocks/demoScenario";
import { supplierWalletSummary } from "../../utils/supplierWallet";

export function SupplierCompanyWalletPage() {
  const invoices = useInvoices();
  const { t } = useLanguage();

  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;

  const wallet = supplierWalletSummary(invoices.data ?? []);
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
              <dd>{DEMO_SUPPLIER_PROFILE.legalName}</dd>
            </div>
            <div>
              <dt>{t("Business registration number", "사업자등록번호")}</dt>
              <dd>{DEMO_SUPPLIER_PROFILE.businessRegistrationNumber}</dd>
            </div>
            <div>
              <dt>{t("Representative", "대표자")}</dt>
              <dd>{t(DEMO_SUPPLIER_PROFILE.representativeEnglish, DEMO_SUPPLIER_PROFILE.representativeKorean)}</dd>
            </div>
            <div>
              <dt>{t("Company email", "회사 이메일")}</dt>
              <dd>{DEMO_SUPPLIER_PROFILE.email}</dd>
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

        <SolanaWalletConnection
          title={t("Settlement wallet", "정산 지갑")}
          description={t(
            "Early-settlement funds will be paid in USDC to the connected Solana wallet.",
            "조기정산 금액은 연결된 Solana 지갑으로 USDC 지급됩니다.",
          )}
          balanceUsdc={wallet.receivedUsdc}
          onWalletConnected={() => undefined}
          onWalletDisconnected={() => undefined}
        />
      </div>

      <aside className="wallet-security-note">
        <CheckCircle size={17} weight="fill" aria-hidden="true" />
        <div>
          <strong>{t("Wallet security", "지갑 보안")}</strong>
          <p>
            {t(
              "InvoiceX never stores private keys. The connected address is not saved until a separate settlement API is integrated.",
              "InvoiceX는 개인키를 저장하지 않으며, 별도 정산 API가 연동되기 전까지 연결된 주소도 저장하지 않습니다.",
            )}
          </p>
        </div>
      </aside>
    </section>
  );
}
