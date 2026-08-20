import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, act } from "@testing-library/react";
import { Keypair, VersionedTransaction } from "@solana/web3.js";
import type { ReactNode } from "react";
import { beforeEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  confirmBuyerPayment: vi.fn(),
  connection: {
    confirmTransaction: vi.fn(),
    getLatestBlockhash: vi.fn(),
    getTokenAccountBalance: vi.fn(),
    sendRawTransaction: vi.fn(),
  },
  currentAccount: {
    userEmail: "buyer@company.com",
    walletAddress: "",
  },
  ensureEmbeddedSolanaWallet: vi.fn(),
  getAccessToken: vi.fn(),
  linkEmbeddedWallet: vi.fn(),
  liveWalletAddress: "",
  prepareBuyerPayment: vi.fn(),
  signEmbeddedSolanaTransaction: vi.fn(),
  updateCurrentAccount: vi.fn(),
}));

vi.mock("@solana/wallet-adapter-react", () => ({
  useConnection: () => ({ connection: mocks.connection }),
}));

vi.mock("@solana/spl-token", () => ({
  getAssociatedTokenAddressSync: () => "buyer-token-account",
}));

vi.mock("../api/invoices.api", () => ({
  invoiceApi: {
    confirmBuyerPayment: mocks.confirmBuyerPayment,
    prepareBuyerPayment: mocks.prepareBuyerPayment,
  },
}));

vi.mock("../api/onboarding.api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/onboarding.api")>();
  return { ...actual, linkEmbeddedWallet: mocks.linkEmbeddedWallet };
});

vi.mock("../auth/currentAccount", () => ({
  useCurrentPrivyAccount: () => mocks.currentAccount,
  useUpdateCurrentPrivyAccount: () => mocks.updateCurrentAccount,
}));

vi.mock("../auth/SignupAuthContext", () => ({
  useSignupAuth: () => ({
    authenticated: true,
    authenticatedEmail: "buyer@company.com",
    embeddedSolanaWalletReady: true,
    ensureEmbeddedSolanaWallet: mocks.ensureEmbeddedSolanaWallet,
    getAccessToken: mocks.getAccessToken,
    hasEmbeddedSolanaWallet: (address: string) => address === mocks.liveWalletAddress,
    signEmbeddedSolanaTransaction: mocks.signEmbeddedSolanaTransaction,
  }),
}));

vi.mock("../wallet/buyerPaymentTransaction", () => ({
  buildBuyerPaymentTransaction: () => ({ instructions: [] }),
}));

import { useBuyerPayment } from "./useBuyerPayment";

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(VersionedTransaction.prototype, "serialize").mockReturnValue(new Uint8Array([1]));
  mocks.currentAccount.walletAddress = Keypair.generate().publicKey.toBase58();
  mocks.liveWalletAddress = Keypair.generate().publicKey.toBase58();
  const mint = Keypair.generate().publicKey.toBase58();
  const recipient = Keypair.generate().publicKey.toBase58();
  const blockhash = "11111111111111111111111111111111";
  mocks.ensureEmbeddedSolanaWallet.mockResolvedValue({
    address: mocks.liveWalletAddress,
    created: false,
  });
  mocks.getAccessToken.mockResolvedValue("privy-buyer-token");
  mocks.linkEmbeddedWallet.mockResolvedValue({
    embeddedWallet: { address: mocks.liveWalletAddress },
  });
  mocks.prepareBuyerPayment.mockResolvedValue({
    invoiceId: "INV-2026-003",
    buyerWalletAddress: mocks.liveWalletAddress,
    settlementWalletAddress: recipient,
    usdcMintAddress: mint,
    amountUsdc: 3,
    amountBaseUnits: 3_000_000,
    decimals: 6,
    dueDate: "2026-09-18",
    transfers: [{
      recipientWalletAddress: recipient,
      amountUsdc: 3,
      amountBaseUnits: 3_000_000,
    }],
  });
  mocks.connection.getTokenAccountBalance.mockResolvedValue({ value: { amount: "3000000" } });
  mocks.connection.getLatestBlockhash.mockResolvedValue({ blockhash, lastValidBlockHeight: 100 });
  mocks.signEmbeddedSolanaTransaction.mockImplementation(async (_address, transaction) => transaction);
  mocks.connection.sendRawTransaction.mockResolvedValue("buyer-payment-signature");
  mocks.connection.confirmTransaction.mockResolvedValue({ value: { err: null } });
  mocks.confirmBuyerPayment.mockResolvedValue({ id: "INV-2026-003", status: "SETTLED" });
});

test("relinks the live Privy wallet and uses the Privy token for buyer payment", async () => {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  const { result } = renderHook(() => useBuyerPayment("INV-2026-003"), { wrapper });

  await act(async () => {
    await result.current.mutateAsync();
  });

  expect(mocks.linkEmbeddedWallet).toHaveBeenCalledWith(
    "privy-buyer-token",
    mocks.liveWalletAddress,
  );
  expect(mocks.updateCurrentAccount).toHaveBeenCalledWith({
    walletAddress: mocks.liveWalletAddress,
  });
  expect(mocks.prepareBuyerPayment).toHaveBeenCalledWith(
    "INV-2026-003",
    "privy-buyer-token",
  );
  expect(mocks.confirmBuyerPayment).toHaveBeenCalledWith(
    "INV-2026-003",
    "buyer-payment-signature",
    "privy-buyer-token",
  );
});
