import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { InvestorVaultPage } from "./InvestorVaultPage";

const mocks = vi.hoisted(() => ({
  authenticated: false,
  embeddedReady: true,
  hasEmbeddedWallet: true,
  getVault: vi.fn(),
}));

vi.mock("@solana/wallet-adapter-react", () => ({
  useConnection: () => ({ connection: {} }),
  useWallet: () => ({
    connected: false,
    publicKey: null,
    signTransaction: null,
    sendTransaction: null,
  }),
}));
vi.mock("../../api/rwa.api", () => ({
  rwaApi: {
    getVault: mocks.getVault,
  },
}));
vi.mock("../../auth/currentAccount", () => ({
  useCurrentPrivyAccount: () => ({
    userEmail: "investor@company.com",
    walletAddress: "EmbeddedWalletAddress",
  }),
}));
vi.mock("../../auth/SignupAuthContext", () => ({
  useSignupAuth: () => ({
    authenticated: mocks.authenticated,
    embeddedSolanaWalletReady: mocks.embeddedReady,
    hasEmbeddedSolanaWallet: () => mocks.hasEmbeddedWallet,
    signEmbeddedSolanaTransaction: vi.fn(),
  }),
}));
vi.mock("../../hooks/useDevnetUsdcBalance", () => ({
  useDevnetUsdcBalance: () => ({
    balanceUsdc: 20,
    isError: false,
    isLoading: false,
    refresh: vi.fn(),
  }),
}));
vi.mock("../../hooks/useInvestorDashboard", () => ({
  useInvestorDashboard: () => ({ data: { availableVaultUsdc: 0, outstandingPrincipalUsdc: 2 } }),
}));
vi.mock("../../i18n/LanguageContext", () => ({
  useLanguage: () => ({ t: (_english: string, korean: string) => korean }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mocks.authenticated = false;
  mocks.embeddedReady = true;
  mocks.hasEmbeddedWallet = true;
  mocks.getVault.mockReturnValue(new Promise(() => undefined));
});

test("sends a password-login investor through Privy verification instead of silently disabling deposit", () => {
  render(<MemoryRouter><InvestorVaultPage /></MemoryRouter>);

  expect(screen.getByRole("link", { name: "이메일 인증 후 USDC 예치" }))
    .toHaveAttribute("href", "/signup");
  expect(screen.queryByRole("button", { name: "USDC 예치" })).not.toBeInTheDocument();
});

test("enables deposit when the authenticated Privy embedded wallet is ready", () => {
  mocks.authenticated = true;
  render(<MemoryRouter><InvestorVaultPage /></MemoryRouter>);

  expect(screen.getByRole("button", { name: "USDC 예치" })).toBeEnabled();
});
