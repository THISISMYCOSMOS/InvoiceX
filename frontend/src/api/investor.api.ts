import { scenarioAdapter } from "./client";

export const investorApi = {
  getDashboard: () => scenarioAdapter.getInvestorDashboard(),
};
