import type { LoginRole } from "../auth/demoAccounts";

export interface LoginResult {
  accessToken: string;
  tokenType: "bearer";
  role: LoginRole;
  email: string;
  expiresAt: string;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const apiBase = `${apiBaseUrl.replace(/\/$/, "")}/api/v1`;

export const authApi = {
  async login(role: LoginRole, email: string, password: string): Promise<LoginResult> {
    const response = await fetch(`${apiBase}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role, email, password }),
    });
    if (!response.ok) throw new Error("로그인 정보를 확인해 주세요.");
    return response.json() as Promise<LoginResult>;
  },
};
