import type { ReactNode } from "react";

/**
 * Keep the wallet adapter mounted across role routes. MetaMask emits account
 * changes itself, so switching Supplier/Investor must not revoke the existing
 * site connection or clear the selected adapter.
 */
export function WalletRoleSwitchGuard({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
