import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { SupplierCompanyWalletPage } from "./SupplierCompanyWalletPage";

const mocks = vi.hoisted(() => ({
  currentAccount: {
    companyName: "Demo Supplier",
    countryCode: "KR",
    registrationNumber: "1234567890",
    role: "SUPPLIER",
    userEmail: "demo@example.com",
    userName: "Demo User",
    userPhone: "010-1234-5678",
    userTitle: "Manager",
    walletAddress: "DemoWalletAddress",
  },
  getSettlementWallet: vi.fn(),
  updateCompanyProfile: vi.fn(),
  updateCurrentAccount: vi.fn(),
}));

vi.mock("../../api/onboarding.api", () => ({
  updateCompanyProfile: mocks.updateCompanyProfile,
}));

vi.mock("../../api/rwa.api", () => ({
  rwaApi: {
    getSettlementWallet: mocks.getSettlementWallet,
    updateSettlementWallet: vi.fn(),
    withdrawAccount: vi.fn(),
  },
}));

vi.mock("../../auth/currentAccount", () => ({
  useCurrentPrivyAccount: () => mocks.currentAccount,
  useUpdateCurrentPrivyAccount: () => mocks.updateCurrentAccount,
}));

vi.mock("../../auth/demoAccounts", () => ({
  clearDemoSession: vi.fn(),
  getDemoSession: () => ({ accessToken: "member-token" }),
}));

vi.mock("../../auth/SignupAuthContext", () => ({
  useSignupAuth: () => ({
    authenticated: false,
    getAccessToken: vi.fn().mockResolvedValue(null),
    logout: vi.fn(),
  }),
}));

vi.mock("../../hooks/useDevnetUsdcBalance", () => ({
  useDevnetUsdcBalance: () => ({ balanceUsdc: 0, isError: false, isLoading: false }),
}));

vi.mock("../../i18n/LanguageContext", () => ({
  useLanguage: () => ({ t: (english: string) => english }),
}));

beforeEach(() => {
  mocks.getSettlementWallet.mockReset().mockResolvedValue({
    walletType: "EMBEDDED",
    address: "DemoWalletAddress",
    embeddedWalletAddress: "DemoWalletAddress",
  });
  mocks.updateCurrentAccount.mockReset();
  mocks.updateCompanyProfile.mockReset().mockResolvedValue({
    user: {
      email: "demo@example.com",
      name: "Updated User",
      phone: "010-9876-5432",
      title: "CEO",
    },
    company: {
      name: "Updated Supplier",
      registrationNumber: "9876543210",
    },
  });
});

test("edits and persists the authenticated supplier company profile", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><SupplierCompanyWalletPage /></MemoryRouter>);

  await user.click(screen.getByRole("button", { name: "Edit" }));
  await user.clear(screen.getByLabelText("Legal company name"));
  await user.type(screen.getByLabelText("Legal company name"), "Updated Supplier");
  await user.clear(screen.getByLabelText("Company registration number"));
  await user.type(screen.getByLabelText("Company registration number"), "9876543210");
  await user.clear(screen.getByLabelText("Representative"));
  await user.type(screen.getByLabelText("Representative"), "Updated User");
  await user.clear(screen.getByLabelText("Representative title"));
  await user.type(screen.getByLabelText("Representative title"), "CEO");
  await user.clear(screen.getByLabelText("Contact number"));
  await user.type(screen.getByLabelText("Contact number"), "01098765432");
  await user.click(screen.getByRole("button", { name: "Save changes" }));

  await waitFor(() => expect(mocks.updateCompanyProfile).toHaveBeenCalledWith("member-token", {
    company: {
      name: "Updated Supplier",
      type: "SUPPLIER",
      countryCode: "KR",
      registrationNumber: "987-65-43210",
    },
    representative: {
      name: "Updated User",
      title: "CEO",
      phone: "010-9876-5432",
    },
  }));
  expect(mocks.updateCurrentAccount).toHaveBeenCalledWith({
    companyName: "Updated Supplier",
    registrationNumber: "9876543210",
    userName: "Updated User",
    userPhone: "010-9876-5432",
    userTitle: "CEO",
  });
  expect(screen.getByRole("status")).toHaveTextContent("Company information has been saved.");
});
