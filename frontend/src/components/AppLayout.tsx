import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { Brand } from "./Brand";
import { LanguageToggle } from "./LanguageToggle";
import { useLanguage } from "../i18n/LanguageContext";
import { useInvoice } from "../hooks/useInvoice";

export function AppLayout({ children }: { children: ReactNode }) {
  const { pathname, search } = useLocation();
  const { t } = useLanguage();
  const isSupplier = pathname.startsWith("/supplier");
  const isBuyer = pathname.startsWith("/buyer");
  const detailInvoiceId = pathname.match(/^\/(?:supplier|buyer)\/invoices\/([^/]+)/)?.[1] ?? "";
  const detailInvoice = useInvoice(detailInvoiceId, Boolean(detailInvoiceId));
  const role = isSupplier ? "SUPPLIER" : isBuyer ? "BUYER" : pathname.startsWith("/investor") ? "INVESTOR" : "DEMO";
  const company = isSupplier ? "Alpha Components" : isBuyer ? "Prime Mobility" : pathname.startsWith("/investor") ? "Nova Capital" : "InvoiceX Demo";
  const isBuyerPayment = isBuyer && search.includes("section=payment");
  const isSupplierOffer = isSupplier && detailInvoice.data?.status === "OFFER_READY";
  const homePath = isSupplier ? "/supplier" : isBuyer ? "/buyer" : pathname.startsWith("/investor") ? "/investor" : "/dev/demo";
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
      : undefined;

  return (
    <div className="screen-stage">
      {caption && <p className="screen-caption">{caption}</p>}
      <div className="app-shell">
        <header className="topbar">
          <Link className="topbar__brand" to={homePath} aria-label="InvoiceX home">
            <Brand />
          </Link>
          <div className="topbar__user">
            <LanguageToggle />
            {isBuyer && detailInvoiceId && (
              <span className="topbar-status-pill topbar-status-pill--green">
                {isBuyerPayment ? "Payment pending" : "Verification request"}
              </span>
            )}
            {isSupplierOffer && (
              <span className="topbar-status-pill topbar-status-pill--blue">Buyer verified</span>
            )}
            {isSupplier && pathname === "/supplier" && <span className="wallet-label">Wallet · 8xK2...p91Q</span>}
            <span className="user-avatar" aria-hidden="true" />
            <strong>{company}</strong>
          </div>
        </header>

        <div className="app-shell__body">
          <aside className={`sidebar sidebar--${role.toLowerCase()}`}>
            <div className="role-chip">{role}</div>
            {isSupplier ? (
              <nav className="sidebar-nav" aria-label="Supplier navigation">
                <Link className={pathname === "/supplier" ? "is-active" : ""} to="/supplier">{t("Overview", "개요")}</Link>
                <Link className={pathname !== "/supplier" ? "is-active" : ""} to="/supplier/invoices/new">{t("Invoices", "인보이스")}</Link>
                <span>{t("Company & Wallet", "회사 및 지갑")}</span>
              </nav>
            ) : isBuyer ? (
              <nav className="sidebar-nav" aria-label="Buyer navigation">
                <Link className={pathname === "/buyer" ? "is-active" : ""} to="/buyer">Overview</Link>
                <Link
                  className={pathname.startsWith("/buyer/invoices") && !isBuyerPayment ? "is-active" : ""}
                  to="/buyer/invoices/INV-2026-001?section=verification"
                >
                  Verification Requests
                </Link>
                <Link
                  className={isBuyerPayment ? "is-active" : ""}
                  to="/buyer/invoices/INV-2026-001?section=payment"
                >
                  Payment Schedule
                </Link>
                <span>Completed</span>
              </nav>
            ) : (
              <nav className="sidebar-nav" aria-label={`${role} navigation`}>
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
