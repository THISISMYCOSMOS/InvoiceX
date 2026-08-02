import { useWallet } from "@solana/wallet-adapter-react";
import { useEffect, useRef, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { walletRoleFromPath, type WalletRole } from "./walletRole";

/**
 * A browser wallet adapter has a single active account for the site. Clear it
 * when moving between supplier and investor routes so one role's connected
 * wallet is never presented as the other role's wallet.
 */
export function WalletRoleSwitchGuard({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const { disconnect, select } = useWallet();
  const role = walletRoleFromPath(pathname);
  const previousRoleRef = useRef<WalletRole>(role);

  useEffect(() => {
    const previousRole = previousRoleRef.current;
    if (previousRole === role) return;

    previousRoleRef.current = role;
    if (!previousRole || !role) return;

    select(null);
    void disconnect().catch(() => undefined);
  }, [disconnect, role, select]);

  return <>{children}</>;
}
