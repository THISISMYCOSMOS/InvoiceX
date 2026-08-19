import { createContext, useContext } from "react";
import type { CompanyType } from "../api/onboarding.api";

export type CurrentPrivyAccount = {
  companyName: string;
  countryCode: string;
  registrationNumber: string;
  role: CompanyType;
  userEmail: string;
  userName: string | null;
  userPhone?: string | null;
  userTitle: string | null;
  walletAddress: string;
};

export type CurrentPrivyAccountUpdate = Partial<Pick<
  CurrentPrivyAccount,
  "companyName" | "registrationNumber" | "userName" | "userPhone" | "userTitle"
>>;

export const CurrentAccountContext = createContext<CurrentPrivyAccount | undefined>(undefined);
export const CurrentAccountUpdateContext = createContext<(update: CurrentPrivyAccountUpdate) => void>(() => undefined);

export function useCurrentPrivyAccount() {
  return useContext(CurrentAccountContext);
}

export function useUpdateCurrentPrivyAccount() {
  return useContext(CurrentAccountUpdateContext);
}
