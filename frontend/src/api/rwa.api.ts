import { isMockApi } from "./client";
import { getAuthorizationHeader } from "../auth/authorization";
import type { AgentActivityTimeline } from "../types/agents";

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

export interface InvestorMandate {
  id: string;
  ownerWalletAddress: string;
  vaultAddress: string;
  policy: MandatePolicyInput;
  canonicalMessage: string;
  signature: string;
  status: "ACTIVE" | "REVOKED";
  createdAt: string;
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

export interface InvestmentCriteriaBuyer {
  id: string;
  name: string;
}

export interface SettlementWallet {
  walletType: "EMBEDDED" | "EXTERNAL";
  address: string;
  embeddedWalletAddress: string;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const apiBase = `${apiBaseUrl.replace(/\/$/, "")}/api/v1`;

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const authorization = await getAuthorizationHeader();
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: { ...authorization, ...init.headers },
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => undefined);
    const message = typeof body === "object" && body !== null && "message" in body
      ? String(body.message)
      : "요청을 처리하지 못했습니다. 다시 시도해 주세요.";
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

async function requestOrNullOn404<T>(path: string): Promise<T | null> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: await getAuthorizationHeader(),
  });
  if (response.status === 404) return null;
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
  async getAgentActivity(invoiceId: string, role: "Supplier" | "Investor"): Promise<AgentActivityTimeline | null> {
    if (isMockApi) return null;
    return request<AgentActivityTimeline>(
      `/invoices/${encodeURIComponent(invoiceId)}/agent-activity?viewerRole=${encodeURIComponent(role)}`,
      { method: "GET" },
    );
  },
  async getInvestmentCriteriaBuyers(): Promise<InvestmentCriteriaBuyer[]> {
    if (isMockApi) {
      return [
        { id: "BUYER_PRIME", name: "Prime Mobility" },
        { id: "BUYER_ORBIT", name: "Orbit Components" },
        { id: "BUYER_DAON", name: "Daon Logistics" },
        { id: "BUYER_VERTEX", name: "Vertex Retail" },
      ];
    }
    return request<InvestmentCriteriaBuyer[]>("/reference/investment-criteria/buyers", {
      method: "GET",
    });
  },

  async getSettlementWallet(): Promise<SettlementWallet | null> {
    if (isMockApi) return null;
    return request<SettlementWallet>("/auth/settlement-wallet", { method: "GET" });
  },

  async updateSettlementWallet(
    walletType: SettlementWallet["walletType"],
    address?: string,
  ): Promise<SettlementWallet | null> {
    if (isMockApi) return null;
    return request<SettlementWallet>("/auth/settlement-wallet", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ walletType, address }),
    });
  },

  async withdrawAccount(): Promise<void> {
    if (isMockApi) return;
    await request<{ onboardingStatus: "WITHDRAWN" }>("/auth/account", {
      method: "DELETE",
    });
  },

  async saveSupplierWallet(walletAddress: string): Promise<void> {
    if (isMockApi) return;
    const authorization = await getAuthorizationHeader();
    const response = await fetch(`${apiBase}/supplier/wallet`, {
      method: "POST",
      headers: { ...authorization, "Content-Type": "application/json" },
      body: JSON.stringify({ walletAddress }),
    });
    if (!response.ok) throw new Error("정산 지갑을 저장하지 못했습니다. 다시 연결해 주세요.");
  },

  async getActiveMandate(ownerWalletAddress: string): Promise<InvestorMandate | null> {
    if (isMockApi) return null;
    return requestOrNullOn404<InvestorMandate>(
      `/investor/mandates/active?ownerWalletAddress=${encodeURIComponent(ownerWalletAddress)}`,
    );
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
