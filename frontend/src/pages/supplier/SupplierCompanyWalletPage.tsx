import { BuildingOffice, CheckCircle, Copy, LinkSimple, Plug, Wallet } from "@phosphor-icons/react";
import { useState } from "react";
import { useLanguage } from "../../i18n/LanguageContext";

const WALLET_ADDRESS = "8xK2f7yZQmP8Y5BwL9Vx3dTs7cR2nJ6p91Q";

export function SupplierCompanyWalletPage() {
  const [isConnected, setIsConnected] = useState(true);
  const [copied, setCopied] = useState(false);
  const { t } = useLanguage();

  const copyWalletAddress = async () => {
    await navigator.clipboard?.writeText(WALLET_ADDRESS);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
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
            <span className="verification-pill">
              <CheckCircle size={13} weight="fill" aria-hidden="true" />
              {t("Verified", "인증 완료")}
            </span>
          </header>

          <dl className="company-details">
            <div>
              <dt>{t("Legal company name", "법인명")}</dt>
              <dd>Alpha Components Co., Ltd.</dd>
            </div>
            <div>
              <dt>{t("Business registration number", "사업자등록번호")}</dt>
              <dd>123-45-67890</dd>
            </div>
            <div>
              <dt>{t("Representative", "대표자")}</dt>
              <dd>{t("Minjun Kim", "김민준")}</dd>
            </div>
            <div>
              <dt>{t("Company email", "회사 이메일")}</dt>
              <dd>finance@alphacomponents.com</dd>
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

        <article className="wallet-card">
          <header className="settings-card__header">
            <span className="settings-card__icon settings-card__icon--navy" aria-hidden="true">
              <Wallet size={18} weight="fill" />
            </span>
            <div>
              <h2>{t("Settlement wallet", "정산 지갑")}</h2>
              <p>{t("Solana Devnet · Demo connection", "Solana Devnet · 데모 연결")}</p>
            </div>
            <span className={`wallet-status ${isConnected ? "is-connected" : ""}`}>
              <span aria-hidden="true" />
              {isConnected ? t("Connected", "연결됨") : t("Not connected", "연결 안 됨")}
            </span>
          </header>

          {isConnected ? (
            <>
              <div className="wallet-address-panel">
                <div>
                  <span>{t("Wallet address", "지갑 주소")}</span>
                  <strong>{WALLET_ADDRESS}</strong>
                </div>
                <button type="button" className="wallet-copy-button" onClick={copyWalletAddress}>
                  <Copy size={14} weight="bold" aria-hidden="true" />
                  {copied ? t("Copied", "복사됨") : t("Copy", "복사")}
                </button>
              </div>

              <div className="wallet-metrics">
                <div>
                  <span>{t("Available balance", "사용 가능 잔액")}</span>
                  <strong>24,680 <small>USDC</small></strong>
                </div>
                <div>
                  <span>{t("Network", "네트워크")}</span>
                  <strong>Solana Devnet</strong>
                </div>
                <div>
                  <span>{t("Last connected", "최근 연결")}</span>
                  <strong>2026-07-30 14:22 KST</strong>
                </div>
              </div>

              <div className="wallet-card__footer">
                <p>
                  <CheckCircle size={15} weight="fill" aria-hidden="true" />
                  {t(
                    "This wallet is ready to receive early-settlement proceeds.",
                    "조기정산 대금을 수령할 준비가 완료된 지갑입니다.",
                  )}
                </p>
                <button type="button" className="secondary-button wallet-action" onClick={() => setIsConnected(false)}>
                  <Plug size={14} weight="bold" aria-hidden="true" />
                  {t("Disconnect wallet", "지갑 연결 해제")}
                </button>
              </div>
            </>
          ) : (
            <div className="wallet-empty-state">
              <span aria-hidden="true">
                <LinkSimple size={25} weight="bold" />
              </span>
              <h3>{t("Connect a settlement wallet", "정산 지갑을 연결하세요")}</h3>
              <p>
                {t(
                  "Connect a Solana wallet to receive early-settlement proceeds in USDC.",
                  "조기정산 대금을 USDC로 수령할 Solana 지갑을 연결하세요.",
                )}
              </p>
              <button type="button" className="primary-button wallet-connect-button" onClick={() => setIsConnected(true)}>
                <Wallet size={15} weight="fill" aria-hidden="true" />
                {t("Connect wallet", "지갑 연결")}
              </button>
            </div>
          )}
        </article>
      </div>

      <aside className="wallet-security-note">
        <CheckCircle size={17} weight="fill" aria-hidden="true" />
        <div>
          <strong>{t("Wallet security", "지갑 보안")}</strong>
          <p>
            {t(
              "InvoiceX never stores private keys. Only the connected public address is saved for settlement.",
              "InvoiceX는 개인키를 저장하지 않으며 정산을 위해 연결된 공개 주소만 사용합니다.",
            )}
          </p>
        </div>
      </aside>
    </section>
  );
}
