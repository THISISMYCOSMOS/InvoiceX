import type { ReactNode } from "react";
import {
  CurrentAccountContext,
  CurrentAccountUpdateContext,
  type CurrentPrivyAccount,
  type CurrentPrivyAccountUpdate,
} from "./currentAccount";

export function CurrentAccountProvider({
  account,
  onAccountChange,
  children,
}: {
  account?: CurrentPrivyAccount;
  onAccountChange?: (update: CurrentPrivyAccountUpdate) => void;
  children: ReactNode;
}) {
  return (
    <CurrentAccountUpdateContext.Provider value={onAccountChange ?? (() => undefined)}>
      <CurrentAccountContext.Provider value={account}>
        {children}
      </CurrentAccountContext.Provider>
    </CurrentAccountUpdateContext.Provider>
  );
}
