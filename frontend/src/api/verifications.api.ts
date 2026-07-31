import { scenarioAdapter } from "./client";
import type { BuyerChecklist } from "../types/invoice";

export const verificationApi = {
  getVerifications: () => scenarioAdapter.getVerifications(),
  getVerification: (verificationId: string) => scenarioAdapter.getVerification(verificationId),
  confirmVerification: (verificationId: string, checklist?: BuyerChecklist) =>
    scenarioAdapter.confirmVerification(verificationId, checklist),
  requestRevision: (verificationId: string) => scenarioAdapter.requestRevision(verificationId),
};
