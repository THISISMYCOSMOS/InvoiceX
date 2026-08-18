import type { ReactNode } from "react";
import { CurrentAccountContext, type CurrentPrivyAccount } from "./currentAccount";

export function CurrentAccountProvider({
  account,
  children,
}: {
  account?: CurrentPrivyAccount;
  children: ReactNode;
}) {
  return (
    <CurrentAccountContext.Provider value={account}>
      {children}
    </CurrentAccountContext.Provider>
  );
}
