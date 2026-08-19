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
    countryCode: string;
    registrationNumber: string;
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
    countryCode: string;
    registrationNumber: string;
  };
  representative: {
    name: string;
    title: string;
    phone: string;
  };
  password?: string;
  embeddedWalletAddress: string;
};

export type UpdateCompanyProfileInput = Omit<
  OnboardCompanyInput,
  "password" | "embeddedWalletAddress"
>;

export type OtpClock = {
  serverTimeMs: number;
  expiresInSeconds: number;
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

const privyTokenRetryDelaysMs = [0, 250, 750, 1_500] as const;

function isRetryablePrivyTokenError(cause: unknown): boolean {
  if (!(cause instanceof Error)) return false;
  const error = cause as Error & { code?: string; status?: number };
  return error.code === "PRIVY_TOKEN_INVALID" && error.status === 401;
}

export async function withPrivyAccessTokenRetry<T>(
  getAccessToken: () => Promise<string | null>,
  operation: (token: string) => Promise<T>,
  retryDelaysMs: readonly number[] = privyTokenRetryDelaysMs,
): Promise<T> {
  let lastError: unknown;
  for (const delayMs of retryDelaysMs) {
    if (delayMs > 0) {
      await new Promise<void>((resolve) => window.setTimeout(resolve, delayMs));
    }
    const token = await getAccessToken();
    if (!token) {
      lastError = new Error("Privy Access Token을 확인할 수 없습니다.");
      continue;
    }
    try {
      return await operation(token);
    } catch (cause) {
      if (!isRetryablePrivyTokenError(cause)) throw cause;
      lastError = cause;
    }
  }
  throw lastError ?? new Error("Privy Access Token을 확인할 수 없습니다.");
}

export async function getOtpClock(): Promise<OtpClock> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/otp-clock`, { cache: "no-store" });
  if (!response.ok) throw new Error("인증 코드 유효시간을 서버와 동기화하지 못했습니다.");
  return response.json() as Promise<OtpClock>;
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

export function updateCompanyProfile(
  token: string,
  input: UpdateCompanyProfileInput,
): Promise<OnboardingResponse> {
  return request<OnboardingResponse>("/auth/company-profile", token, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function linkEmbeddedWallet(
  token: string,
  address: string,
): Promise<OnboardingResponse> {
  return request<OnboardingResponse>("/auth/embedded-wallet", token, {
    method: "PUT",
    body: JSON.stringify({ address }),
  });
}
