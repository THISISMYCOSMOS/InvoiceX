import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useInvoice } from "../hooks/useInvoice";
import { useLanguage } from "../i18n/LanguageContext";
import { Brand } from "./Brand";
import { LanguageToggle } from "./LanguageToggle";

export function AppLayout({ children }: { children: ReactNode }) {
  const { pathname, search } = useLocation();
  const { t } = useLanguage();
  const isSupplier = pathname.startsWith("/supplier");
  const isBuyer = pathname.startsWith("/buyer");
  const isInvestor = pathname.startsWith("/investor");
  const isInvestorActivity = pathname.startsWith("/investor/activities/");
  const isInvestorSetup = pathname === "/investor/setup";
  const detailInvoiceId = pathname.match(/^\/(?:supplier|buyer)\/invoices\/([^/]+)/)?.[1] ?? "";
  const detailInvoice = useInvoice(detailInvoiceId, Boolean(detailInvoiceId));
  const role = isSupplier ? "SUPPLIER" : isBuyer ? "BUYER" : isInvestor ? "INVESTOR" : "DEMO";
  const company = isSupplier
    ? "Alpha Components"
    : isBuyer
      ? "Prime Mobility"
      : isInvestor
        ? "Nova Capital"
        : "InvoiceX Demo";
  const isBuyerPayment = isBuyer && search.includes("section=payment");
  const isSupplierOffer = isSupplier && detailInvoice.data?.status === "OFFER_READY";
  const homePath = isSupplier ? "/supplier" : isBuyer ? "/buyer" : isInvestor ? "/investor" : "/dev/demo";
  const caption = isSupplier
    ? pathname === "/supplier"
      ? "01 · SUPPLIER DASHBOARD / 1440 × 900"
      : pathname === "/supplier/invoices/new"
        ? "02 · DOCUMENT UPLOAD / 1440 × 900"
        : isSupplierOffer
          ? "07 · RISK PASSPORT & EARLY SETTLEMENT OFFER / 1440 × 900"
          : undefined
    : isBuyer
      ? pathname === "/buyer"
        ? "05 · BUYER DASHBOARD / 1440 × 900"
        : isBuyerPayment
          ? "10 · BUYER DUE-DATE PAYMENT / 1440 × 900"
          : "06 · BUYER VERIFICATION / 1440 × 900"
      : isInvestor
        ? isInvestorActivity
          ? "10 · TREASURY AGENT DECISION DETAIL / 1440 × 900"
          : pathname === "/investor"
            ? "09 · INVESTOR DASHBOARD / 1440 × 900"
            : undefined
        : undefined;

  return (
    <div className="screen-stage">
      {caption && <p className="screen-caption">{caption}</p>}
      <div className="app-shell">
        <header className="topbar">
          <Link className="topbar__brand" to={homePath} aria-label={t("InvoiceX home", "InvoiceX 홈")}>
            <Brand />
          </Link>
          <div className="topbar__user">
            <LanguageToggle />
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
            {isInvestor && (
              <span className="topbar-status-pill topbar-status-pill--purple">
                {isInvestorActivity
                  ? t("Investment completed", "투자 완료")
                  : t("Auto-invest active", "자동 투자 활성")}
              </span>
            )}
            {isSupplier && pathname === "/supplier" && (
              <span className="wallet-label">Wallet · 8xK2...p91Q</span>
            )}
            {isInvestor && !isInvestorActivity && (
              <span className="wallet-label">Vault · 7VB...0Qe</span>
            )}
            <span className="user-avatar" aria-hidden="true" />
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
                <Link className={pathname !== "/supplier" ? "is-active" : ""} to="/supplier/invoices/new">
                  {t("Invoices", "인보이스")}
                </Link>
                <span>{t("Company & Wallet", "회사 및 지갑")}</span>
              </nav>
            ) : isBuyer ? (
              <nav className="sidebar-nav" aria-label={t("Buyer navigation", "구매기업 내비게이션")}>
                <Link className={pathname === "/buyer" ? "is-active" : ""} to="/buyer">
                  {t("Overview", "개요")}
                </Link>
                <Link
                  className={pathname.startsWith("/buyer/invoices") && !isBuyerPayment ? "is-active" : ""}
                  to="/buyer/invoices/INV-2026-001?section=verification"
                >
                  {t("Verification Requests", "확인 요청")}
                </Link>
                <Link
                  className={isBuyerPayment ? "is-active" : ""}
                  to="/buyer/invoices/INV-2026-001?section=payment"
                >
                  {t("Payment Schedule", "결제 일정")}
                </Link>
                <span>{t("Completed", "완료")}</span>
              </nav>
            ) : isInvestor ? (
              <nav className="sidebar-nav" aria-label={t("Investor navigation", "투자자 내비게이션")}>
                <Link className={pathname === "/investor" ? "is-active" : ""} to="/investor">
                  {t("Overview", "개요")}
                </Link>
                <Link
                  className={isInvestorActivity ? "is-active" : ""}
                  to="/investor/activities/INV-2026-001"
                >
                  {t("Agent Activity", "에이전트 활동")}
                </Link>
                <span>{t("RWA Portfolio", "RWA 포트폴리오")}</span>
                <Link className={isInvestorSetup ? "is-active" : ""} to="/investor/setup">
                  {t("Mandate", "투자 위임")}
                </Link>
                <span>Vault</span>
                {!isInvestorActivity && <span>{t("Settlement Reports", "정산 보고서")}</span>}
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
