import { scenarioAdapter } from "./client";

export const investorApi = {
  getDashboard: () => scenarioAdapter.getInvestorDashboard(),
  prepareDeposit: (investorWalletAddress: string, amountUsdc: number) =>
    scenarioAdapter.prepareInvestorDeposit(investorWalletAddress, amountUsdc),
  confirmDeposit: (referenceId: string, signature: string) =>
    scenarioAdapter.confirmInvestorDeposit(referenceId, signature),
};
