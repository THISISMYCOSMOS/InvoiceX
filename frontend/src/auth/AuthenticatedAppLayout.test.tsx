import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { AuthenticatedAppLayout } from "./AuthenticatedAppLayout";

const mocks = vi.hoisted(() => ({
  authenticated: true as boolean,
  getAccessToken: vi.fn(),
  getAuthMe: vi.fn(),
  logout: vi.fn(),
  ready: true as boolean,
}));

vi.mock("../api/client", () => ({ isMockApi: false }));
vi.mock("../api/onboarding.api", () => ({ getAuthMe: mocks.getAuthMe }));
vi.mock("./SignupAuthContext", () => ({
  useSignupAuth: () => ({
    authenticated: mocks.authenticated,
    getAccessToken: mocks.getAccessToken,
    logout: mocks.logout,
    ready: mocks.ready,
  }),
}));
vi.mock("../components/AppLayout", () => ({
  AppLayout: ({ children, currentPrivyAccount }: {
    children: ReactNode;
    currentPrivyAccount?: { companyName: string };
  }) => (
    <div>
      <span>{currentPrivyAccount?.companyName}</span>
      {children}
    </div>
  ),
}));
vi.mock("./CurrentAccountProvider", () => ({
  CurrentAccountProvider: ({ children }: { children: ReactNode }) => children,
}));

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  mocks.authenticated = true;
  mocks.ready = true;
  mocks.getAccessToken.mockReset().mockResolvedValue("privy-token");
  mocks.getAuthMe.mockReset().mockResolvedValue({
    company: {
      countryCode: "KR",
      registrationNumber: "1234567890",
      name: "Supplier One",
      type: "SUPPLIER",
    },
    embeddedWallet: { address: "embedded-wallet-address" },
    onboardingStatus: "COMPLETED",
    nextPath: "/supplier",
    user: {
      email: "owner@supplier.test",
      name: "Supplier Owner",
      title: "CEO",
    },
  });
});

test("loads the completed Privy company before rendering business pages", async () => {
  render(
    <MemoryRouter initialEntries={["/supplier"]}>
      <AuthenticatedAppLayout><h1>Supplier dashboard</h1></AuthenticatedAppLayout>
    </MemoryRouter>,
  );

  expect(await screen.findByText("Supplier One")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Supplier dashboard" })).toBeInTheDocument();
  expect(mocks.getAuthMe).toHaveBeenCalledWith("privy-token");
});

test("redirects an unauthenticated business route to login", async () => {
  mocks.authenticated = false;
  render(
    <MemoryRouter initialEntries={["/supplier"]}>
      <Routes>
        <Route
          path="/supplier"
          element={<AuthenticatedAppLayout><h1>Supplier dashboard</h1></AuthenticatedAppLayout>}
        />
        <Route path="/login" element={<h1>Login page</h1>} />
      </Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "Login page" })).toBeInTheDocument();
});
