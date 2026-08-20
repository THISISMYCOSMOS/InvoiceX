import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, expect, test, vi } from "vitest";

const investorAddress = "99HjRok4PZoX16d7Zz88S3EW4yjTDaHXJ492GaMJHD1U";
const treasuryAddress = "BDRW9KjvbJA5pxavitWJQ6o3HQiHjmtiZKw5mnJbjXYY";

const mocks = vi.hoisted(() => {
  const confirmTransaction = vi.fn();
  const getLatestBlockhash = vi.fn();
  const getTokenAccountBalance = vi.fn();
  return {
    confirmDeposit: vi.fn(),
    confirmTransaction,
    connection: {
      confirmTransaction,
      getLatestBlockhash,
      getTokenAccountBalance,
    },
    getLatestBlockhash,
    getTokenAccountBalance,
    prepareDeposit: vi.fn(),
    sendTransaction: vi.fn(),
  };
});

const connection = mocks.connection;

vi.mock("@solana/wallet-adapter-react", async () => {
  const { PublicKey } = await import("@solana/web3.js");
  return {
    useConnection: () => ({ connection: mocks.connection }),
    useWallet: () => ({
      connected: true,
      publicKey: new PublicKey("99HjRok4PZoX16d7Zz88S3EW4yjTDaHXJ492GaMJHD1U"),
      sendTransaction: mocks.sendTransaction,
    }),
  };
});

vi.mock("@solana/spl-token", async () => {
  const { PublicKey } = await import("@solana/web3.js");
  return {
    getAssociatedTokenAddressSync: () => new PublicKey("11111111111111111111111111111111"),
  };
});

vi.mock("../wallet/investorDepositTransaction", async () => {
  const { Transaction } = await import("@solana/web3.js");
  return {
    buildInvestorDepositTransaction: () => new Transaction(),
  };
});

vi.mock("../api/investor.api", () => ({
  investorApi: {
    confirmDeposit: mocks.confirmDeposit,
    prepareDeposit: mocks.prepareDeposit,
  },
}));

import { useInvestorDeposit } from "./useInvestorDeposit";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.prepareDeposit.mockResolvedValue({
    referenceId: "DEP-2026-001",
    investorWalletAddress: investorAddress,
    treasuryWalletAddress: treasuryAddress,
    usdcMint: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
    amountUsdc: 20,
    amountBaseUnits: "20000000",
    decimals: 6,
    network: "SOLANA_DEVNET",
  });
  mocks.getTokenAccountBalance.mockResolvedValue({ value: { amount: "20000000" } });
  mocks.getLatestBlockhash.mockResolvedValue({
    blockhash: "11111111111111111111111111111111",
    lastValidBlockHeight: 123,
  });
  mocks.sendTransaction.mockResolvedValue("deposit-signature");
  mocks.confirmTransaction.mockResolvedValue({ value: { err: null } });
  mocks.confirmDeposit.mockResolvedValue({
    referenceId: "DEP-2026-001",
    investorWalletAddress: investorAddress,
    treasuryWalletAddress: treasuryAddress,
    amountUsdc: 20,
    amountBaseUnits: "20000000",
    signature: "deposit-signature",
    status: "CONFIRMED",
    network: "SOLANA_DEVNET",
    explorerUrl: "https://explorer.solana.com/tx/deposit-signature?cluster=devnet",
    confirmedAt: "2026-08-02T00:00:00Z",
  });
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

test("sends the investor deposit through the wallet adapter with Devnet connection context", async () => {
  const { result } = renderHook(() => useInvestorDeposit(), { wrapper: createWrapper() });

  await act(() => result.current.mutateAsync({ amountUsdc: 20 }));

  expect(mocks.sendTransaction).toHaveBeenCalledOnce();
  expect(mocks.sendTransaction).toHaveBeenCalledWith(
    expect.anything(),
    connection,
    { preflightCommitment: "confirmed" },
  );
  expect(mocks.confirmDeposit).toHaveBeenCalledWith("DEP-2026-001", "deposit-signature");
});

test("blocks an unfunded connected account before opening a signing request", async () => {
  mocks.getTokenAccountBalance.mockRejectedValue(new Error("account not found"));
  const { result } = renderHook(() => useInvestorDeposit(), { wrapper: createWrapper() });

  await expect(
    act(() => result.current.mutateAsync({ amountUsdc: 20 })),
  ).rejects.toThrow("연결된 지갑에 Devnet USDC가 없습니다");

  expect(mocks.sendTransaction).not.toHaveBeenCalled();
});
