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
      <button type="button" onClick={() => navigate("/investor/setup")}>Investor setup</button>
    </>
  );
}

function renderGuard() {
  return render(
    <MemoryRouter initialEntries={["/supplier"]}>
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
  test("identifies only supplier and investor paths as wallet roles", () => {
    expect(walletRoleFromPath("/supplier/company-wallet")).toBe("SUPPLIER");
    expect(walletRoleFromPath("/investor/setup")).toBe("INVESTOR");
    expect(walletRoleFromPath("/buyer")).toBeNull();
  });

  test("keeps the browser wallet connected when switching from supplier to investor", async () => {
    const user = userEvent.setup();
    renderGuard();

    await user.click(screen.getByRole("button", { name: "Investor setup" }));

    await waitFor(() => expect(screen.getByText("/investor/setup")).toBeInTheDocument());
    expect(walletState.select).not.toHaveBeenCalled();
    expect(walletState.disconnect).not.toHaveBeenCalled();
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
