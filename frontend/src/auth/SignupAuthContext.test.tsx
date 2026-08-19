import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  defaultSolanaRpcsPlugin: vi.fn(() => ({ id: "solana-rpc-plugin" })),
  privyProvider: vi.fn(({ children }: { children: ReactNode }) => <>{children}</>),
}));

vi.mock("@privy-io/react-auth", () => ({
  getAccessToken: vi.fn(),
  PrivyProvider: mocks.privyProvider,
  useLoginWithEmail: () => ({ loginWithCode: vi.fn(), sendCode: vi.fn() }),
  usePrivy: () => ({
    authenticated: true,
    logout: vi.fn(),
    ready: true,
    user: { email: { address: "Investor@Company.com" } },
  }),
}));

vi.mock("@privy-io/react-auth/solana", () => ({
  defaultSolanaRpcsPlugin: mocks.defaultSolanaRpcsPlugin,
  useCreateWallet: () => ({ createWallet: vi.fn() }),
  useSignMessage: () => ({ signMessage: vi.fn() }),
  useSignTransaction: () => ({ signTransaction: vi.fn() }),
  useWallets: () => ({ ready: true, wallets: [] }),
}));

import { SignupAuthProvider, useSignupAuth } from "./SignupAuthContext";

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubEnv("VITE_PRIVY_APP_ID", "privy-app-id");
});

test("registers Privy's default Solana RPCs so the Devnet signing screen can render", () => {
  render(<SignupAuthProvider><span>InvoiceX</span></SignupAuthProvider>);

  expect(screen.getByText("InvoiceX")).toBeInTheDocument();
  expect(mocks.defaultSolanaRpcsPlugin).toHaveBeenCalledOnce();
  expect(mocks.privyProvider).toHaveBeenCalledWith(
    expect.objectContaining({
      appId: "privy-app-id",
      config: {
        loginMethods: ["email"],
        plugins: [{ id: "solana-rpc-plugin" }],
      },
    }),
    undefined,
  );
});

test("exposes the normalized Privy email so password login preserves the matching wallet session", () => {
  function Consumer() {
    const auth = useSignupAuth();
    return <span>{auth.authenticatedEmail}</span>;
  }

  render(<SignupAuthProvider><Consumer /></SignupAuthProvider>);

  expect(screen.getByText("investor@company.com")).toBeInTheDocument();
});
