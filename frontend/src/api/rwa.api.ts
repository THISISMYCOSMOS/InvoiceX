import { isMockApi } from "./client";

export interface MandatePolicyInput {
  totalInvestmentLimitUsdc: number;
  perInvoiceLimitUsdc: number;
  buyerAllowlist: string[];
  minimumRiskScore: number;
  maximumRemainingTermDays: number;
  expiresAt: string;
}

interface MandateSigningPayload {
  canonicalMessage: string;
}

interface CreatedMandate {
  id: string;
}

interface VaultDepositPreparation {
  transactionBase64: string;
  vaultAddress: string;
  stablecoinMintAddress: string;
  sponsored: boolean;
  sponsorDepositId: string | null;
  sponsorWalletAddress: string | null;
}

export interface VaultBalance {
  ownerWalletAddress: string;
  vaultAddress: string;
  availableUsdc: number;
  updatedAt: string;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const apiBase = `${apiBaseUrl.replace(/\/$/, "")}/api/v1`;

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init);
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => undefined);
    const message = typeof body === "object" && body !== null && "message" in body
      ? String(body.message)
      : "요청을 처리하지 못했습니다. 다시 시도해 주세요.";
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const rwaApi = {
  async saveSupplierWallet(walletAddress: string): Promise<void> {
    if (isMockApi) return;
    const response = await fetch(`${apiBase}/supplier/wallet`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ walletAddress }),
    });
    if (!response.ok) throw new Error("정산 지갑을 저장하지 못했습니다. 다시 연결해 주세요.");
  },

  async prepareMandate(ownerWalletAddress: string, policy: MandatePolicyInput): Promise<MandateSigningPayload> {
    return request<MandateSigningPayload>("/investor/mandates/prepare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerWalletAddress, policy }),
    });
  },

  async createMandate(ownerWalletAddress: string, policy: MandatePolicyInput, signature: string): Promise<CreatedMandate> {
    return request<CreatedMandate>("/investor/mandates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerWalletAddress, policy, signature }),
    });
  },

  async prepareVaultDeposit(ownerWalletAddress: string, amountUsdc: number): Promise<VaultDepositPreparation> {
    return request<VaultDepositPreparation>("/investor/vault/deposits/prepare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerWalletAddress, amountUsdc }),
    });
  },

  async getVault(ownerWalletAddress: string): Promise<VaultBalance> {
    return request<VaultBalance>(
      `/investor/vault?ownerWalletAddress=${encodeURIComponent(ownerWalletAddress)}`,
      { method: "GET" },
    );
  },

  async confirmVaultDeposit(
    ownerWalletAddress: string,
    amountUsdc: number,
    signature: string,
  ): Promise<VaultBalance> {
    return request<VaultBalance>("/investor/vault/deposits/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerWalletAddress, amountUsdc, signature }),
    });
  },

  async sponsorVaultDeposit(
    ownerWalletAddress: string,
    sponsorDepositId: string,
    signedTransactionBase64: string,
  ): Promise<VaultBalance> {
    return request<VaultBalance>("/investor/vault/deposits/sponsor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerWalletAddress, sponsorDepositId, signedTransactionBase64 }),
    });
  },
};
