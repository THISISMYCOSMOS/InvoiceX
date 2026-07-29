import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { RoleSwitcher } from "./RoleSwitcher";

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header>
        <nav aria-label="주요 메뉴">
          <Link to="/supplier">InvoiceX</Link>
          <Link to="/supplier">Supplier</Link>
          <Link to="/buyer">Buyer</Link>
          <Link to="/investor">Investor</Link>
        </nav>
        <RoleSwitcher />
      </header>
      <main>{children}</main>
    </>
  );
}
