import { useWallet } from "@solana/wallet-adapter-react";
import { useEffect, useRef, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { walletRoleFromPath, type WalletRole } from "./walletRole";

/**
 * This demo uses one browser wallet extension for all role routes. Clearing the
 * adapter when that role changes prevents a supplier's active account from
 * appearing as the investor's wallet (and vice versa).
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
    if (!previousRole && !role) return;

    select(null);
    void disconnect().catch(() => undefined);
  }, [disconnect, role, select]);

  return <>{children}</>;
}
