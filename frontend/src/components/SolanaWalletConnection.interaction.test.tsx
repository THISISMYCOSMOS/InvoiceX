import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { LanguageProvider } from "../i18n/LanguageContext";

const walletState = vi.hoisted(() => ({
  connect: vi.fn<() => Promise<void>>(),
  connected: false,
  connecting: false,
  disconnect: vi.fn<() => Promise<void>>(),
  publicKey: null as { toBase58: () => string } | null,
  select: vi.fn(),
  wallet: null as { adapter: { name: string } } | null,
  wallets: [{ adapter: { name: "Phantom" } }],
}));

vi.mock("@solana/wallet-adapter-react", () => ({
  useWallet: () => walletState,
}));

vi.mock("../hooks/useDevnetUsdcBalance", () => ({
  useDevnetUsdcBalance: () => ({
    balanceUsdc: 19,
    isLoading: false,
    isError: false,
    refresh: vi.fn(),
  }),
}));

import { SolanaWalletConnection } from "./SolanaWalletConnection";

const address = "8xK2f7yZQmP8Y5BwL9Vx3dTs7cR2nJ6p91Q";

function renderConnection() {
  return render(
    <LanguageProvider>
      <SolanaWalletConnection title="Settlement wallet" description="Wallet description" />
    </LanguageProvider>,
  );
}

beforeEach(() => {
  walletState.connect.mockReset();
  walletState.disconnect.mockReset();
  walletState.select.mockReset();
  walletState.connected = false;
  walletState.connecting = false;
  walletState.publicKey = null;
  walletState.wallet = null;
  walletState.wallets = [{ adapter: { name: "Phantom" } }];
  walletState.disconnect.mockResolvedValue();
});

describe("SolanaWalletConnection", () => {
  test("selects a wallet and presents a rejection as a Korean user message", async () => {
    const user = userEvent.setup();
    walletState.connect.mockRejectedValue(new Error("User rejected the request"));
    const view = renderConnection();

    await user.click(screen.getByRole("button", { name: "Connect Solana wallet" }));
    await user.click(screen.getByRole("button", { name: "Phantom Connect" }));
    expect(walletState.select).toHaveBeenCalledWith("Phantom");

    walletState.wallet = { adapter: { name: "Phantom" } };
    view.rerender(
      <LanguageProvider>
        <SolanaWalletConnection title="Settlement wallet" description="Wallet description" />
      </LanguageProvider>,
    );

    await waitFor(() => expect(walletState.connect).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("alert")).toHaveTextContent("지갑 연결 요청이 취소되었습니다.");
  });

  test("shows an address and disconnects once connected", async () => {
    const user = userEvent.setup();
    walletState.connected = true;
    walletState.publicKey = { toBase58: () => address };
    walletState.wallet = { adapter: { name: "Phantom" } };
    renderConnection();

    expect(screen.getByText("8xK2...p91Q")).toBeInTheDocument();
    expect(screen.getByText((_, element) => (
      element?.tagName === "STRONG" && element.textContent === "19 USDC"
    ))).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy address" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Disconnect wallet" }));
    expect(walletState.disconnect).toHaveBeenCalledTimes(1);
    expect(walletState.select).toHaveBeenCalledWith(null);
  });

  test("reconnects a previously selected wallet through the same connection path", async () => {
    walletState.wallet = { adapter: { name: "Phantom" } };
    walletState.connect.mockResolvedValue();
    renderConnection();

    await waitFor(() => expect(walletState.connect).toHaveBeenCalledTimes(1));
  });

  test("reactivates the connection button when an adapter leaves a stale connecting state", async () => {
    const user = userEvent.setup();
    walletState.connected = true;
    walletState.publicKey = { toBase58: () => address };
    walletState.wallet = { adapter: { name: "Phantom" } };
    const view = renderConnection();

    await user.click(screen.getByRole("button", { name: "Disconnect wallet" }));
    walletState.connected = false;
    walletState.connecting = true;
    walletState.publicKey = null;
    walletState.wallet = null;
    view.rerender(
      <LanguageProvider>
        <SolanaWalletConnection title="Settlement wallet" description="Wallet description" />
      </LanguageProvider>,
    );

    expect(screen.getByRole("button", { name: "Connect Solana wallet" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Connecting wallet..." })).not.toBeInTheDocument();
  });
});
