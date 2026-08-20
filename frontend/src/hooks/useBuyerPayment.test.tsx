import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, expect, test, vi } from "vitest";

const buyerAddress = "ERkaRrW8SQm9nSfucNNkCqRU3sdLRsJNZrxMRCUYwq3G";
const settlementAddress = "BDRW9KjvbJA5pxavitWJQ6o3HQiHjmtiZKw5mnJbjXYY";

const mocks = vi.hoisted(() => {
  const confirmTransaction = vi.fn();
  const getLatestBlockhash = vi.fn();
  const getTokenAccountBalance = vi.fn();
  const sendRawTransaction = vi.fn();
  const sendTransaction = vi.fn();
  return {
    confirmBuyerPayment: vi.fn(),
    confirmTransaction,
    connection: {
      confirmTransaction,
      getLatestBlockhash,
      getTokenAccountBalance,
      sendRawTransaction,
    },
    getLatestBlockhash,
    getTokenAccountBalance,
    hasEmbeddedSolanaWallet: vi.fn(),
    prepareBuyerPayment: vi.fn(),
    sendRawTransaction,
    sendTransaction,
    signEmbeddedSolanaTransaction: vi.fn(),
    wallet: {
      connected: false,
      publicKey: null as { toBase58: () => string } | null,
      sendTransaction,
    },
  };
});

vi.mock("@solana/wallet-adapter-react", () => ({
  useConnection: () => ({ connection: mocks.connection }),
  useWallet: () => mocks.wallet,
}));

vi.mock("@solana/spl-token", async () => {
  const { PublicKey } = await import("@solana/web3.js");
  return {
    getAssociatedTokenAddressSync: () => new PublicKey("11111111111111111111111111111111"),
  };
});

vi.mock("../auth/SignupAuthContext", () => ({
  useSignupAuth: () => ({
    hasEmbeddedSolanaWallet: mocks.hasEmbeddedSolanaWallet,
    signEmbeddedSolanaTransaction: mocks.signEmbeddedSolanaTransaction,
  }),
}));

vi.mock("../wallet/buyerPaymentTransaction", () => ({
  buildBuyerPaymentTransaction: () => ({
    feePayer: null,
    recentBlockhash: null,
    serialize: () => new Uint8Array([4, 5, 6]),
  }),
}));

vi.mock("../api/invoices.api", () => ({
  invoiceApi: {
    confirmBuyerPayment: mocks.confirmBuyerPayment,
    prepareBuyerPayment: mocks.prepareBuyerPayment,
  },
}));

import { useBuyerPayment } from "./useBuyerPayment";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.wallet.connected = false;
  mocks.wallet.publicKey = null;
  mocks.prepareBuyerPayment.mockResolvedValue({
    invoiceId: "INV-2026-001",
    buyerWalletAddress: buyerAddress,
    settlementWalletAddress: settlementAddress,
    usdcMintAddress: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
    amountUsdc: 5,
    amountBaseUnits: 5_000_000,
    decimals: 6,
    dueDate: "2026-09-18",
    transfers: [{
      recipientWalletAddress: settlementAddress,
      amountUsdc: 5,
      amountBaseUnits: 5_000_000,
    }],
    demoDueDateBypass: true,
  });
  mocks.hasEmbeddedSolanaWallet.mockReturnValue(true);
  mocks.getTokenAccountBalance.mockResolvedValue({ value: { amount: "5000000" } });
  mocks.getLatestBlockhash.mockResolvedValue({
    blockhash: "11111111111111111111111111111111",
    lastValidBlockHeight: 123,
  });
  mocks.signEmbeddedSolanaTransaction.mockResolvedValue(new Uint8Array([1, 2, 3]));
  mocks.sendRawTransaction.mockResolvedValue("buyer-payment-signature");
  mocks.confirmTransaction.mockResolvedValue({ value: { err: null } });
  mocks.confirmBuyerPayment.mockResolvedValue({ id: "INV-2026-001", status: "SETTLED" });
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

test("signs and broadcasts buyer payment with the matching Privy embedded wallet", async () => {
  const { result } = renderHook(() => useBuyerPayment("INV-2026-001"), {
    wrapper: createWrapper(),
  });

  await act(() => result.current.mutateAsync());

  expect(mocks.signEmbeddedSolanaTransaction).toHaveBeenCalledWith(
    buyerAddress,
    expect.any(Uint8Array),
  );
  expect(mocks.sendRawTransaction).toHaveBeenCalledWith(
    new Uint8Array([1, 2, 3]),
    { preflightCommitment: "confirmed" },
  );
  expect(mocks.confirmBuyerPayment).toHaveBeenCalledWith(
    "INV-2026-001",
    "buyer-payment-signature",
  );
});

test("keeps the matching external wallet payment path available", async () => {
  mocks.wallet.connected = true;
  mocks.wallet.publicKey = { toBase58: () => buyerAddress };
  mocks.hasEmbeddedSolanaWallet.mockReturnValue(false);
  mocks.sendTransaction.mockResolvedValue("external-payment-signature");
  const { result } = renderHook(() => useBuyerPayment("INV-2026-001"), {
    wrapper: createWrapper(),
  });

  await act(() => result.current.mutateAsync());

  expect(mocks.sendTransaction).toHaveBeenCalledWith(
    expect.objectContaining({ feePayer: expect.anything() }),
    mocks.connection,
    { preflightCommitment: "confirmed" },
  );
  expect(mocks.signEmbeddedSolanaTransaction).not.toHaveBeenCalled();
  expect(mocks.sendRawTransaction).not.toHaveBeenCalled();
  expect(mocks.confirmBuyerPayment).toHaveBeenCalledWith(
    "INV-2026-001",
    "external-payment-signature",
  );
});
