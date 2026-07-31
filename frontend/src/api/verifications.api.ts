import { scenarioAdapter } from "./client";

export const verificationApi = {
  getVerifications: () => scenarioAdapter.getVerifications(),
  getVerification: (verificationId: string) => scenarioAdapter.getVerification(verificationId),
  confirmVerification: (verificationId: string) => scenarioAdapter.confirmVerification(verificationId),
};
