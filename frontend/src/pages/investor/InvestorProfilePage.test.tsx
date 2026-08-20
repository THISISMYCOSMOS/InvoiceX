import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { InvestorProfilePage } from "./InvestorProfilePage";

const mocks = vi.hoisted(() => ({
  currentAccount: {
    companyName: "Nova Capital",
    countryCode: "KR",
    registrationNumber: "123456789",
    role: "INVESTOR",
    userEmail: "investor@company.com",
    userName: "Alex Morgan",
    userPhone: "415-555-0123",
    userTitle: "CFO",
    walletAddress: "InvestorEmbeddedWalletAddress",
  },
  updateCompanyProfile: vi.fn(),
  updateCurrentAccount: vi.fn(),
}));

vi.mock("../../api/onboarding.api", () => ({
  updateCompanyProfile: mocks.updateCompanyProfile,
}));

vi.mock("../../auth/currentAccount", () => ({
  useCurrentPrivyAccount: () => mocks.currentAccount,
  useUpdateCurrentPrivyAccount: () => mocks.updateCurrentAccount,
}));

vi.mock("../../auth/demoAccounts", () => ({
  getDemoSession: () => ({ accessToken: "investor-token" }),
}));

vi.mock("../../auth/SignupAuthContext", () => ({
  useSignupAuth: () => ({ getAccessToken: vi.fn().mockResolvedValue(null) }),
}));

vi.mock("../../hooks/useDevnetUsdcBalance", () => ({
  useDevnetUsdcBalance: () => ({ balanceUsdc: 125.5, isError: false, isLoading: false }),
}));

vi.mock("../../i18n/LanguageContext", () => ({
  useLanguage: () => ({ t: (english: string) => english }),
}));

beforeEach(() => {
  mocks.updateCurrentAccount.mockReset();
  mocks.updateCompanyProfile.mockReset().mockResolvedValue({
    user: {
      email: "investor@company.com",
      name: "Taylor Lee",
      phone: "212-555-0199",
      title: "CEO",
    },
    company: {
      name: "Updated Capital",
      registrationNumber: "987654321",
    },
  });
});

test("shows the authenticated investor embedded wallet", () => {
  render(<MemoryRouter><InvestorProfilePage /></MemoryRouter>);

  expect(screen.getByText("Embedded wallet")).toBeInTheDocument();
  expect(screen.getByText("InvestorEmbeddedWalletAddress")).toBeInTheDocument();
  expect(screen.getByText("125.5")).toBeInTheDocument();
  expect(screen.getByText("US")).toBeInTheDocument();
  expect(screen.queryByText("KR")).not.toBeInTheDocument();
  expect(screen.queryByText("No wallet connected")).not.toBeInTheDocument();
});

test("edits and persists the authenticated investor company profile", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><InvestorProfilePage /></MemoryRouter>);

  await user.click(screen.getByRole("button", { name: "Edit" }));
  await user.clear(screen.getByLabelText("Legal company name"));
  await user.type(screen.getByLabelText("Legal company name"), "Updated Capital");
  await user.clear(screen.getByLabelText("US EIN"));
  await user.type(screen.getByLabelText("US EIN"), "987654321");
  await user.clear(screen.getByLabelText("Representative"));
  await user.type(screen.getByLabelText("Representative"), "Taylor Lee");
  await user.clear(screen.getByLabelText("Representative title"));
  await user.type(screen.getByLabelText("Representative title"), "CEO");
  await user.clear(screen.getByLabelText("Contact number"));
  await user.type(screen.getByLabelText("Contact number"), "2125550199");
  await user.click(screen.getByRole("button", { name: "Save" }));

  await waitFor(() => expect(mocks.updateCompanyProfile).toHaveBeenCalledWith("investor-token", {
    company: {
      name: "Updated Capital",
      type: "INVESTOR",
      countryCode: "US",
      registrationNumber: "98-7654321",
    },
    representative: {
      name: "Taylor Lee",
      title: "CEO",
      phone: "212-555-0199",
    },
  }));
  expect(mocks.updateCurrentAccount).toHaveBeenCalledWith({
    companyName: "Updated Capital",
    registrationNumber: "987654321",
    userName: "Taylor Lee",
    userPhone: "212-555-0199",
    userTitle: "CEO",
  });
  expect(screen.getByRole("status")).toHaveTextContent("Company information has been saved.");
});
