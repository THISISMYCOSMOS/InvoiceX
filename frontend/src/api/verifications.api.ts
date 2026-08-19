import { scenarioAdapter } from "./client";
import type { BuyerRejectionReason } from "../types/invoice";

export const verificationApi = {
  getVerifications: () => scenarioAdapter.getVerifications(),
  getVerification: (verificationId: string) => scenarioAdapter.getVerification(verificationId),
  confirmVerification: (verificationId: string) => scenarioAdapter.confirmVerification(verificationId),
  rejectVerification: (
    verificationId: string,
    reasonCode: BuyerRejectionReason,
    detail?: string,
  ) => scenarioAdapter.rejectVerification(verificationId, reasonCode, detail),
};
