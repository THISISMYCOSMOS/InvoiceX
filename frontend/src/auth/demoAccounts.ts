export type LoginRole = "Supplier" | "Buyer" | "Investor";
export type SessionAuthMode = "DEMO" | "MEMBER";

export interface DemoAccount {
  role: LoginRole;
  email: string;
  password: string;
}

export interface DemoSession {
  role: LoginRole;
  email: string;
  authenticatedAt: string;
  accessToken?: string;
  authMode?: SessionAuthMode;
}

export const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  { role: "Supplier", email: "supplier@company.com", password: "supplier" },
  { role: "Buyer", email: "buyer@company.com", password: "buyer" },
  { role: "Investor", email: "investor@company.com", password: "investor" },
] as const;

export const DEMO_SESSION_KEY = "invoicex-demo-session";

export function authenticateDemoAccount(
  role: LoginRole,
  email: string,
  password: string,
): DemoAccount | undefined {
  const normalizedEmail = email.trim().toLowerCase();
  return DEMO_ACCOUNTS.find(
    (account) =>
      account.role === role
      && account.email === normalizedEmail
      && account.password === password,
  );
}

export function saveDemoSession(
  account: Pick<DemoAccount, "role" | "email">,
  remember: boolean,
  accessToken?: string,
  authMode: SessionAuthMode = "DEMO",
) {
  const session: DemoSession = {
    role: account.role,
    email: account.email,
    authenticatedAt: new Date().toISOString(),
    accessToken,
    authMode,
  };
  const target = remember ? window.localStorage : window.sessionStorage;
  const other = remember ? window.sessionStorage : window.localStorage;

  other.removeItem(DEMO_SESSION_KEY);
  target.setItem(DEMO_SESSION_KEY, JSON.stringify(session));
}

export function getDemoSession(): DemoSession | undefined {
  const values = [window.sessionStorage.getItem(DEMO_SESSION_KEY), window.localStorage.getItem(DEMO_SESSION_KEY)];
  for (const value of values) {
    if (!value) continue;
    try {
      const session = JSON.parse(value) as DemoSession;
      if (session.role && session.email) return session;
    } catch {
      // Treat an invalid persisted value as logged out.
    }
  }
  return undefined;
}

export function clearDemoSession() {
  window.sessionStorage.removeItem(DEMO_SESSION_KEY);
  window.localStorage.removeItem(DEMO_SESSION_KEY);
}
