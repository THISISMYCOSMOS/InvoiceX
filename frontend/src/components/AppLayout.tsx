import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { RoleSwitcher } from "./RoleSwitcher";

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="sticky top-0 z-10">
        <nav aria-label="주요 메뉴">
          <Link to="/supplier">InvoiceX</Link>
          <Link to="/supplier">Supplier</Link>
          <Link to="/buyer">Buyer</Link>
          <Link to="/investor">Investor</Link>
        </nav>
        <RoleSwitcher />
      </header>
      <main className="px-4 sm:px-6">{children}</main>
    </>
  );
}
