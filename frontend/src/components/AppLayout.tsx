import { useEffect, useState, type ChangeEvent, type ReactNode } from "react";
import { Bell, CheckCircle } from "@phosphor-icons/react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { authApi } from "../api/auth.api";
import { isMockApi } from "../api/client";
import { DEMO_ACCOUNTS, DEMO_SESSION_KEY, saveDemoSession } from "../auth/demoAccounts";
import { getInvoiceDisplayReference, useInvoices } from "../hooks/useInvoices";
import { useLanguage } from "../i18n/LanguageContext";
import type { Invoice } from "../types/invoice";
import { Brand } from "./Brand";
import { LanguageToggle } from "./LanguageToggle";
import type { CurrentPrivyAccount } from "../auth/currentAccount";

export function AppLayout({
  children,
  currentPrivyAccount,
}: {
  children: ReactNode;
  currentPrivyAccount?: CurrentPrivyAccount;
}) {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const isSupplier = pathname.startsWith("/supplier");
  const isBuyer = pathname.startsWith("/buyer");
  const isBuyerProfile = pathname === "/buyer/profile";
  const isInvestor = pathname.startsWith("/investor");
  const isInvestorActivity = pathname.startsWith("/investor/activities/");
  const isInvestorPolicy = pathname === "/investor/investment-policy";
  const isInvestorFundsConversion = pathname === "/investor/funds-conversion";
  const isInvestorVault = pathname === "/investor/vault";
  const isInvestorProfile = pathname === "/investor/profile";
  const detailInvoiceId = pathname.match(/^\/(?:supplier|buyer)\/invoices\/([^/]+)/)?.[1] ?? "";
  const invoices = useInvoices();
  const detailInvoice = invoices.data?.find((invoice) => invoice.id === detailInvoiceId);
  const isBuyerPaymentComplete = detailInvoice?.status === "SETTLED";
  const [isSwitchingRole, setIsSwitchingRole] = useState(false);
  const [roleSwitchError, setRoleSwitchError] = useState<string>();
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
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
  const homePath = isSupplier ? "/supplier" : isBuyer ? "/buyer" : isInvestor ? "/investor" : "/dev/demo";
  const profilePath = isSupplier ? "/supplier/company-wallet" : isBuyer ? "/buyer/profile" : isInvestor ? "/investor/profile" : null;
  const supplierNotifications = isSupplier ? getSupplierNotifications(invoices.data ?? []) : [];

  useEffect(() => {
    setIsNotificationsOpen(false);
  }, [pathname]);
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
      <div className={`app-shell app-shell--${role.toLowerCase()}`}>
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
            <div className="topbar-notifications">
              <button
                className="notification-button"
                type="button"
                aria-label={t("Notifications", "알림")}
                aria-controls="supplier-notifications"
                aria-expanded={isNotificationsOpen}
                onClick={() => setIsNotificationsOpen((current) => !current)}
              >
                <Bell size={16} weight="bold" aria-hidden="true" />
                {supplierNotifications.length > 0 && (
                  <span className="notification-button__count">{supplierNotifications.length}</span>
                )}
              </button>
              {isNotificationsOpen && (
                <section className="notification-popover" id="supplier-notifications" aria-label={t("Notifications", "알림")}>
                  <header>
                    <strong>{t("Notifications", "알림")}</strong>
                    <span>{supplierNotifications.length}</span>
                  </header>
                  {supplierNotifications.length === 0 ? (
                    <p>{t("No new notifications.", "새로운 알림이 없습니다.")}</p>
                  ) : (
                    <ul>
                      {supplierNotifications.map((notification) => (
                        <li key={notification.id}>
                          <CheckCircle size={16} weight="fill" aria-hidden="true" />
                          <div>
                            <strong>{notification.title}</strong>
                            <span>{notification.description}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}
            </div>
            {isBuyer && detailInvoiceId && (
              <span className="topbar-status-pill topbar-status-pill--green">
                {isBuyerPayment
                  ? isBuyerPaymentComplete
                    ? t("Payment complete", "결제 완료")
                    : t("Payment pending", "결제 대기")
                  : t("Verification request", "확인 요청")}
              </span>
            )}
            {profilePath ? <Link className="topbar__company" to={profilePath}>{company}</Link> : <strong>{company}</strong>}
          </div>
        </header>

        <div className="app-shell__body">
          <aside className={`sidebar sidebar--${role.toLowerCase()}`}>
            <div className="role-chip">{role}</div>
            {isSupplier ? (
              <nav className="sidebar-nav" aria-label={t("Supplier navigation", "공급기업 내비게이션")}>
                <Link className={pathname === "/supplier" ? "is-active" : ""} to="/supplier">
                  {t("Dashboard", "대시보드")}
                </Link>
                <Link className={pathname.startsWith("/supplier/invoices") ? "is-active" : ""} to="/supplier/invoices/new">
                  {t("Invoice registration", "인보이스 등록")}
                </Link>
                <Link className={pathname === "/supplier/funds-conversion" ? "is-active" : ""} to="/supplier/funds-conversion">
                  {t("Funds conversion", "자금 전환")}
                </Link>
                <Link className={pathname === "/supplier/company-wallet" ? "is-active" : ""} to="/supplier/company-wallet">
                  {t("Profile", "프로필")}
                </Link>
              </nav>
            ) : isBuyer ? (
              <nav className="sidebar-nav" aria-label={t("Buyer navigation", "구매기업 내비게이션")}>
                <Link className={pathname === "/buyer" ? "is-active" : ""} to="/buyer">
                  {t("Dashboard", "대시보드")}
                </Link>
                <Link
                  className={pathname === "/buyer/verification" || (pathname.startsWith("/buyer/invoices") && !isBuyerPayment) ? "is-active" : ""}
                  to="/buyer/verification"
                >
                  {t("Verification Requests", "확인 요청")}
                </Link>
                <Link
                  className={pathname === "/buyer/payment" || isBuyerPayment ? "is-active" : ""}
                  to="/buyer/payment"
                >
                  {t("Payment List", "결제 목록")}
                </Link>
                <Link className={isBuyerProfile ? "is-active" : ""} to="/buyer/profile">
                  {t("Profile", "프로필")}
                </Link>
              </nav>
            ) : isInvestor ? (
              <nav className="sidebar-nav" aria-label={t("Investor navigation", "투자자 내비게이션")}>
                <Link className={pathname === "/investor" ? "is-active" : ""} to="/investor">
                  {t("Dashboard", "대시보드")}
                </Link>
                <Link
                  className={isInvestorActivity ? "is-active" : ""}
                  to="/investor/activities"
                >
                  {t("Agent Activity", "에이전트 활동")}
                </Link>
                <Link className={isInvestorPolicy ? "is-active" : ""} to="/investor/investment-policy">
                  {t("Investment Policy", "투자 정책")}
                </Link>
                <Link className={isInvestorFundsConversion ? "is-active" : ""} to="/investor/funds-conversion">
                  {t("Funds conversion", "자금 전환")}
                </Link>
                <Link className={isInvestorVault ? "is-active" : ""} to="/investor/vault">
                  {t("Vault", "자산 보관함")}
                </Link>
                <Link className={isInvestorProfile ? "is-active" : ""} to="/investor/profile">
                  {t("Profile", "프로필")}
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

function getSupplierNotifications(invoices: Invoice[]) {
  const reviewCompleteStatuses = new Set([
    "BUYER_VERIFIED",
    "RISK_ASSESSING",
    "OFFER_READY",
    "RWA_ISSUED",
    "FUNDING",
    "FUNDED",
    "SETTLED",
    "REPAYMENT_PENDING",
    "SETTLING",
  ]);
  const earlySettlementCompleteStatuses = new Set(["FUNDED", "SETTLED", "REPAYMENT_PENDING", "SETTLING"]);

  return invoices.flatMap((invoice) => {
    const reference = getInvoiceDisplayReference(invoice);
    const notifications = [] as Array<{ id: string; title: string; description: string }>;
    if (reviewCompleteStatuses.has(invoice.status)) {
      notifications.push({
        id: `${invoice.id}-review-complete`,
        title: "인보이스 검토 완료",
        description: `${reference} 인보이스 검토가 완료되었습니다.`,
      });
    }
    if (earlySettlementCompleteStatuses.has(invoice.status)) {
      notifications.push({
        id: `${invoice.id}-early-settlement-complete`,
        title: "조기정산 완료",
        description: `${reference}의 조기정산 금액이 지급되었습니다.`,
      });
    }
    return notifications;
  });
}
