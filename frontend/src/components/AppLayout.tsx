import { useState, type ChangeEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { authApi } from "../api/auth.api";
import { isMockApi } from "../api/client";
import { DEMO_ACCOUNTS, DEMO_SESSION_KEY, saveDemoSession } from "../auth/demoAccounts";
import { useInvoice } from "../hooks/useInvoice";
import { useInvoices } from "../hooks/useInvoices";
import { useLanguage } from "../i18n/LanguageContext";
import { Brand } from "./Brand";
import { LanguageToggle } from "./LanguageToggle";
import type { CurrentPrivyAccount } from "../auth/currentAccount";

export function AppLayout({
  children,
  currentPrivyAccount,
  onPrivyLogout,
}: {
  children: ReactNode;
  currentPrivyAccount?: CurrentPrivyAccount;
  onPrivyLogout?: () => Promise<void>;
}) {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const isSupplier = pathname.startsWith("/supplier");
  const isBuyer = pathname.startsWith("/buyer");
  const isInvestor = pathname.startsWith("/investor");
  const isInvestorActivity = pathname.startsWith("/investor/activities/");
  const isInvestorPolicy = pathname === "/investor/investment-policy";
  const isInvestorVault = pathname === "/investor/vault";
  const isInvestorProfile = pathname === "/investor/profile";
  const detailInvoiceId = pathname.match(/^\/(?:supplier|buyer)\/invoices\/([^/]+)/)?.[1] ?? "";
  const detailInvoice = useInvoice(detailInvoiceId, Boolean(detailInvoiceId));
  const invoices = useInvoices();
  const [isSwitchingRole, setIsSwitchingRole] = useState(false);
  const [roleSwitchError, setRoleSwitchError] = useState<string>();
  const role = isSupplier ? "SUPPLIER" : isBuyer ? "BUYER" : isInvestor ? "INVESTOR" : "DEMO";
  const company = currentPrivyAccount?.companyName ?? (
    isSupplier
      ? "Alpha Components"
      : isBuyer
        ? "Prime Mobility"
        : isInvestor
          ? "Nova Capital"
          : "InvoiceX Demo"
  );
  const isBuyerPayment = isBuyer && search.includes("section=payment");
  const isSupplierOffer = isSupplier && detailInvoice.data?.status === "OFFER_READY";
  const homePath = isSupplier ? "/supplier" : isBuyer ? "/buyer" : isInvestor ? "/investor" : "/dev/demo";
  const buyerVerificationInvoice = invoices.data?.find((invoice) => invoice.status === "BUYER_REVIEW") ?? invoices.data?.[0];
  const buyerPaymentInvoice = invoices.data?.find((invoice) => (
    invoice.status === "FUNDED" || invoice.status === "REPAYMENT_PENDING" || invoice.status === "SETTLING"
  )) ?? buyerVerificationInvoice;
  const buyerVerificationPath = buyerVerificationInvoice
    ? `/buyer/invoices/${buyerVerificationInvoice.id}?section=verification`
    : "/buyer";
  const buyerPaymentPath = buyerPaymentInvoice
    ? `/buyer/invoices/${buyerPaymentInvoice.id}?section=payment`
    : "/buyer";
  const switchRole = async (event: ChangeEvent<HTMLSelectElement>) => {
    const nextRole = event.target.value;
    const account = DEMO_ACCOUNTS.find((candidate) => candidate.role.toUpperCase() === nextRole);
    if (!account) return;

    setIsSwitchingRole(true);
    setRoleSwitchError(undefined);
    try {
      const remember = Boolean(window.localStorage.getItem(DEMO_SESSION_KEY));
      if (isMockApi) {
        saveDemoSession(account, remember);
      } else {
        const authenticatedAccount = await authApi.login(account.role, account.email, account.password);
        saveDemoSession(authenticatedAccount, remember, authenticatedAccount.accessToken);
      }
      navigate(`/${nextRole.toLowerCase()}`);
    } catch {
      setRoleSwitchError(t("Could not switch the demo role. Please try again.", "데모 역할을 전환하지 못했습니다. 다시 시도해 주세요."));
    } finally {
      setIsSwitchingRole(false);
    }
  };
  return (
    <div className="screen-stage">
      <div className="app-shell">
        <header className="topbar">
          <Link className="topbar__brand" to={homePath} aria-label={t("InvoiceX home", "InvoiceX 홈")}>
            <Brand />
          </Link>
          <div className="topbar__user">
            {currentPrivyAccount ? (
              <span className="role-switcher">
                {currentPrivyAccount.role === "SUPPLIER"
                  ? t("Supplier", "공급기업")
                  : currentPrivyAccount.role === "BUYER"
                    ? t("Buyer", "구매기업")
                    : t("Investor", "투자자")}
              </span>
            ) : (
              <label className="role-switcher">
                <span className="sr-only">{t("Switch role", "역할 변경")}</span>
                <select
                  aria-label={t("Switch role", "역할 변경")}
                  value={role === "DEMO" ? "" : role}
                  onChange={(event) => void switchRole(event)}
                  disabled={isSwitchingRole}
                >
                  {role === "DEMO" && <option value="">{t("Switch role", "역할 변경")}</option>}
                  <option value="SUPPLIER">{t("Supplier", "공급기업")}</option>
                  <option value="BUYER">{t("Buyer", "구매기업")}</option>
                  <option value="INVESTOR">{t("Investor", "투자자")}</option>
                </select>
              </label>
            )}
            {roleSwitchError && <span className="topbar-role-error" role="status">{roleSwitchError}</span>}
            <LanguageToggle />
            {onPrivyLogout && (
              <button type="button" onClick={() => void onPrivyLogout()}>
                {t("Sign out", "로그아웃")}
              </button>
            )}
            {isBuyer && detailInvoiceId && (
              <span className="topbar-status-pill topbar-status-pill--green">
                {isBuyerPayment
                  ? t("Payment pending", "결제 대기")
                  : t("Verification request", "확인 요청")}
              </span>
            )}
            {isSupplierOffer && (
              <span className="topbar-status-pill topbar-status-pill--blue">
                {t("Buyer verified", "구매기업 확인 완료")}
              </span>
            )}
            <strong>{company}</strong>
          </div>
        </header>

        <div className="app-shell__body">
          <aside className={`sidebar sidebar--${role.toLowerCase()}`}>
            <div className="role-chip">{role}</div>
            {isSupplier ? (
              <nav className="sidebar-nav" aria-label={t("Supplier navigation", "공급기업 내비게이션")}>
                <Link className={pathname === "/supplier" ? "is-active" : ""} to="/supplier">
                  {t("Overview", "개요")}
                </Link>
                <Link className={pathname.startsWith("/supplier/invoices") ? "is-active" : ""} to="/supplier/invoices/new">
                  {t("Invoices", "인보이스")}
                </Link>
                <Link className={pathname === "/supplier/company-wallet" ? "is-active" : ""} to="/supplier/company-wallet">
                  {t("Settings", "설정")}
                </Link>
              </nav>
            ) : isBuyer ? (
              <nav className="sidebar-nav" aria-label={t("Buyer navigation", "구매기업 내비게이션")}>
                <Link className={pathname === "/buyer" ? "is-active" : ""} to="/buyer">
                  {t("Overview", "개요")}
                </Link>
                <Link
                  className={pathname.startsWith("/buyer/invoices") && !isBuyerPayment ? "is-active" : ""}
                  to={buyerVerificationPath}
                >
                  {t("Verification Requests", "확인 요청")}
                </Link>
                <Link
                  className={isBuyerPayment ? "is-active" : ""}
                  to={buyerPaymentPath}
                >
                  {t("Payment Schedule", "결제 일정")}
                </Link>
              </nav>
            ) : isInvestor ? (
              <nav className="sidebar-nav" aria-label={t("Investor navigation", "투자자 내비게이션")}>
                <Link className={pathname === "/investor" ? "is-active" : ""} to="/investor">
                  {t("Dashboard", "Dashboard")}
                </Link>
                <Link
                  className={isInvestorActivity ? "is-active" : ""}
                  to="/investor/activities"
                >
                  {t("Agent Activity", "에이전트 활동")}
                </Link>
                <Link className={isInvestorPolicy ? "is-active" : ""} to="/investor/investment-policy">
                  {t("Investment Policy", "Investment Policy")}
                </Link>
                <Link className={isInvestorVault ? "is-active" : ""} to="/investor/vault">
                  Vault
                </Link>
                <Link className={isInvestorProfile ? "is-active" : ""} to="/investor/profile">
                  Profile
                </Link>
              </nav>
            ) : (
              <nav className="sidebar-nav" aria-label={t(`${role} navigation`, `${role} 내비게이션`)}>
                <Link to={`/${role.toLowerCase()}`}>{t("Overview", "개요")}</Link>
                <Link to="/login">{t("Switch role", "역할 전환")}</Link>
              </nav>
            )}
          </aside>
          <main className="app-content">{children}</main>
        </div>
      </div>
    </div>
  );
}
