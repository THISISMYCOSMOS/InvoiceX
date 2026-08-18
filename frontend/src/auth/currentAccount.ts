import { createContext, useContext } from "react";
import type { CompanyType } from "../api/onboarding.api";

export type CurrentPrivyAccount = {
  companyName: string;
  businessRegistrationNumber: string;
  role: CompanyType;
  userEmail: string;
  userName: string | null;
  userTitle: string | null;
  walletAddress: string;
};

export const CurrentAccountContext = createContext<CurrentPrivyAccount | undefined>(undefined);

export function useCurrentPrivyAccount() {
  return useContext(CurrentAccountContext);
}
