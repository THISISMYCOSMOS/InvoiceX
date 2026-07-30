export type LoginRole = "Supplier" | "Buyer" | "Investor";

export interface DemoAccount {
  role: LoginRole;
  email: string;
  password: string;
}

export interface DemoSession {
  role: LoginRole;
  email: string;
  authenticatedAt: string;
}

export const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  { role: "Supplier", email: "supplier@company.com", password: "supplier" },
  { role: "Buyer", email: "buyer@company.com", password: "buyer" },
  { role: "Investor", email: "invester@company.com", password: "invester" },
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

export function saveDemoSession(account: DemoAccount, remember: boolean) {
  const session: DemoSession = {
    role: account.role,
    email: account.email,
    authenticatedAt: new Date().toISOString(),
  };
  const target = remember ? window.localStorage : window.sessionStorage;
  const other = remember ? window.sessionStorage : window.localStorage;

  other.removeItem(DEMO_SESSION_KEY);
  target.setItem(DEMO_SESSION_KEY, JSON.stringify(session));
}
