import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const walletState = vi.hoisted(() => ({
  disconnect: vi.fn<() => Promise<void>>(),
  select: vi.fn(),
}));

vi.mock("@solana/wallet-adapter-react", () => ({
  useWallet: () => walletState,
}));

import { WalletRoleSwitchGuard } from "./WalletRoleSwitchGuard";
import { walletRoleFromPath } from "./walletRole";

function RoleNavigation() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <>
      <p>{pathname}</p>
      <button type="button" onClick={() => navigate("/supplier/company-wallet")}>Supplier settings</button>
      <button type="button" onClick={() => navigate("/buyer")}>Buyer overview</button>
      <button type="button" onClick={() => navigate("/investor/profile")}>Investor profile</button>
    </>
  );
}

function renderGuard(initialPath = "/supplier") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <WalletRoleSwitchGuard>
        <RoleNavigation />
      </WalletRoleSwitchGuard>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  walletState.disconnect.mockReset();
  walletState.select.mockReset();
  walletState.disconnect.mockResolvedValue();
});

describe("WalletRoleSwitchGuard", () => {
  test("identifies every company-role path as a wallet role", () => {
    expect(walletRoleFromPath("/supplier/company-wallet")).toBe("SUPPLIER");
    expect(walletRoleFromPath("/buyer")).toBe("BUYER");
    expect(walletRoleFromPath("/investor/profile")).toBe("INVESTOR");
    expect(walletRoleFromPath("/login")).toBeNull();
  });

  test("clears the active wallet when switching from supplier to investor", async () => {
    const user = userEvent.setup();
    renderGuard();

  await user.click(screen.getByRole("button", { name: "Investor profile" }));

    await waitFor(() => expect(screen.getByText("/investor/profile")).toBeInTheDocument());
    expect(walletState.select).toHaveBeenCalledWith(null);
    expect(walletState.disconnect).toHaveBeenCalledTimes(1);
  });

  test("clears the active wallet when switching from supplier to buyer", async () => {
    const user = userEvent.setup();
    renderGuard();

    await user.click(screen.getByRole("button", { name: "Buyer overview" }));

    await waitFor(() => expect(screen.getByText("/buyer")).toBeInTheDocument());
    expect(walletState.select).toHaveBeenCalledWith(null);
    expect(walletState.disconnect).toHaveBeenCalledTimes(1);
  });

  test("clears the active wallet when switching from buyer to investor", async () => {
    const user = userEvent.setup();
    renderGuard("/buyer");

  await user.click(screen.getByRole("button", { name: "Investor profile" }));

    await waitFor(() => expect(screen.getByText("/investor/profile")).toBeInTheDocument());
    expect(walletState.select).toHaveBeenCalledWith(null);
    expect(walletState.disconnect).toHaveBeenCalledTimes(1);
  });

  test("keeps the wallet connected while moving within the same role", async () => {
    const user = userEvent.setup();
    renderGuard();

    await user.click(screen.getByRole("button", { name: "Supplier settings" }));

    await waitFor(() => expect(screen.getByText("/supplier/company-wallet")).toBeInTheDocument());
    expect(walletState.select).not.toHaveBeenCalled();
    expect(walletState.disconnect).not.toHaveBeenCalled();
  });
});
