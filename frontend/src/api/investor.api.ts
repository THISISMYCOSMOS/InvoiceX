import { scenarioAdapter } from "./client";
import type { InvestorMandate } from "../types/invoice";

export const investorApi = {
  getDashboard: () => scenarioAdapter.getInvestorDashboard(),
  getMandate: () => scenarioAdapter.getInvestorMandate(),
  saveMandate: (mandate: InvestorMandate) => scenarioAdapter.saveInvestorMandate(mandate),
};
