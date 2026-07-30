import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { Brand } from "./Brand";
import { LanguageToggle } from "./LanguageToggle";
import { useLanguage } from "../i18n/LanguageContext";

export function AppLayout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const { t } = useLanguage();
  const isSupplier = pathname.startsWith("/supplier");
  const isBuyer = pathname.startsWith("/buyer");
  const role = isSupplier ? "SUPPLIER" : isBuyer ? "BUYER" : pathname.startsWith("/investor") ? "INVESTOR" : "DEMO";
  const company = isSupplier ? "Alpha Components" : isBuyer ? "Prime Mobility" : pathname.startsWith("/investor") ? "Nova Capital" : "InvoiceX Demo";
  const caption = isSupplier
    ? pathname === "/supplier"
      ? "01 · SUPPLIER DASHBOARD / 1440 × 900"
      : pathname === "/supplier/invoices/new"
        ? "02 · DOCUMENT UPLOAD / 1440 × 900"
        : undefined
    : undefined;

  return (
    <div className="screen-stage">
      {caption && <p className="screen-caption">{caption}</p>}
      <div className="app-shell">
        <header className="topbar">
          <Link className="topbar__brand" to="/supplier" aria-label="InvoiceX home">
            <Brand />
          </Link>
          <div className="topbar__user">
            <LanguageToggle />
            {isSupplier && pathname === "/supplier" && <span className="wallet-label">Wallet · 8xK2...p91Q</span>}
            <span className="user-avatar" aria-hidden="true" />
            <strong>{company}</strong>
          </div>
        </header>

        <div className="app-shell__body">
          <aside className="sidebar">
            <div className="role-chip">{role}</div>
            {isSupplier ? (
              <nav className="sidebar-nav" aria-label="Supplier navigation">
                <Link className={pathname === "/supplier" ? "is-active" : ""} to="/supplier">{t("Overview", "개요")}</Link>
                <Link className={pathname !== "/supplier" ? "is-active" : ""} to="/supplier/invoices/new">{t("Invoices", "인보이스")}</Link>
                <span>{t("Company & Wallet", "회사 및 지갑")}</span>
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
