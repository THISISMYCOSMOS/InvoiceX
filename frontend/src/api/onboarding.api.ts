const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type CompanyType = "SUPPLIER" | "BUYER" | "INVESTOR";
export type OnboardingStatus =
  | "NEEDS_COMPANY_PROFILE"
  | "PROVISIONING_EMBEDDED_WALLET"
  | "COMPLETED";

export type OnboardingResponse = {
  user: {
    id: string;
    privyUserId: string;
    email: string;
    name: string | null;
    title: string | null;
    phone: string | null;
    companyId: string | null;
    onboardingStatus: OnboardingStatus;
  };
  company: {
    id: string;
    name: string;
    type: CompanyType;
    businessRegistrationNumber: string;
    kybStatus: string;
    status: string;
  } | null;
  embeddedWallet: {
    id: string;
    companyId: string;
    privyUserId: string;
    walletType: "EMBEDDED";
    privyWalletId: string;
    chain: "SOLANA";
    address: string;
    status: string;
  } | null;
  onboardingStatus: OnboardingStatus;
  nextPath: string;
};

export type OnboardCompanyInput = {
  company: {
    name: string;
    type: CompanyType;
    businessRegistrationNumber: string;
  };
  representative: {
    name: string;
    title: string;
    phone: string;
  };
};

export class OnboardingApiError extends Error {
  constructor(
    message: string,
    readonly code?: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}/api/v1${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as {
      code?: string;
      message?: string;
    } | null;
    throw new OnboardingApiError(
      body?.message ?? "회원가입 요청을 처리하지 못했습니다.",
      body?.code,
      response.status,
    );
  }
  return response.json() as Promise<T>;
}

export function getAuthMe(token: string): Promise<OnboardingResponse> {
  return request<OnboardingResponse>("/auth/me", token);
}

export function onboardCompany(
  token: string,
  input: OnboardCompanyInput,
): Promise<OnboardingResponse> {
  return request<OnboardingResponse>("/onboarding/company", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}
