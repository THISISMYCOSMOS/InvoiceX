import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { scenarioAdapter } from "../../api/client";
import { CurrentAccountProvider } from "../../auth/CurrentAccountProvider";
import { DEMO_FUNDING_TRANSACTION, DEMO_INVOICE } from "../../mocks/demoScenario";
import { SupplierDashboardPage } from "./SupplierDashboardPage";
import { getDashboardSummary } from "./supplierDashboardSummary";

const useDevnetUsdcBalanceMock = vi.hoisted(() => vi.fn());
const getSettlementWalletMock = vi.hoisted(() => vi.fn());

vi.mock("../../api/rwa.api", () => ({
  rwaApi: {
    getSettlementWallet: getSettlementWalletMock,
  },
}));

vi.mock("../../hooks/useDevnetUsdcBalance", () => ({
  useDevnetUsdcBalance: useDevnetUsdcBalanceMock.mockImplementation(() => ({
    address: "8xK2f7yZQmP8Y5BwL9Vx3dTs7cR2nJ6p91Q",
    balanceUsdc: 1.25,
    isLoading: false,
    isError: false,
  })),
}));

beforeEach(async () => {
  await scenarioAdapter.reset();
  getSettlementWalletMock.mockReset().mockResolvedValue({
    walletType: "EXTERNAL",
    address: "BzVQsk3NKMnV7dbDWMGznFovtMfnu3orPwqj3F7kmyEP",
    embeddedWalletAddress: "8xK2f7yZQmP8Y5BwL9Vx3dTs7cR2nJ6p91Q",
  });
});

function renderDashboard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CurrentAccountProvider account={{
          companyName: "Supplier One",
          countryCode: "KR",
          registrationNumber: "1234567890",
          role: "SUPPLIER",
          userEmail: "owner@supplier.test",
          userName: "Jiyoon",
          userTitle: "Manager",
          walletAddress: "8xK2f7yZQmP8Y5BwL9Vx3dTs7cR2nJ6p91Q",
        }}>
          <SupplierDashboardPage />
        </CurrentAccountProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("derives supplier dashboard statistics from actual invoice states and links each invoice to its progress page", async () => {
  await scenarioAdapter.analyzeInvoice("INV-2026-001");
  await scenarioAdapter.requestVerification("INV-2026-001");
  renderDashboard();

  expect(await screen.findByRole("heading", { name: "Good morning, Jiyoon" })).toBeInTheDocument();
  expect(screen.getByText("USDC wallet balance")).toBeInTheDocument();
  expect(screen.getByText("In early settlement")).toBeInTheDocument();
  expect(screen.getByText("Waiting for buyer")).toBeInTheDocument();
  expect(screen.getByText("Received by current wallet")).toBeInTheDocument();
  expect(within(screen.getByLabelText("USDC wallet balance")).getByText("1.25")).toBeInTheDocument();
  expect(within(screen.getByLabelText("USDC wallet balance")).getByText("Connected wallet")).toBeInTheDocument();
  expect(within(screen.getByLabelText("In early settlement")).getByText("0")).toBeInTheDocument();
  expect(within(screen.getByLabelText("Waiting for buyer")).getByText("1")).toBeInTheDocument();
  expect(within(screen.getByLabelText("Received by current wallet")).getByText("0")).toBeInTheDocument();
  expect(useDevnetUsdcBalanceMock).toHaveBeenCalledWith("BzVQsk3NKMnV7dbDWMGznFovtMfnu3orPwqj3F7kmyEP");
  expect(screen.getByRole("table", { name: "Recent invoices" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "New invoice" })).toHaveAttribute("href", "/supplier/invoices/new");
  expect(await screen.findByRole("link", { name: "View invoice INV-2026-001" })).toHaveAttribute("href", "/supplier/invoices/INV-2026-001");
  expect(screen.getByText("Buyer review")).toBeInTheDocument();
});

test("does not report a confirmed transfer sent to another wallet as received", () => {
  const fundedInvoice = {
    ...DEMO_INVOICE,
    status: "FUNDED" as const,
    fundingTransaction: DEMO_FUNDING_TRANSACTION,
  };

  expect(
    getDashboardSummary([fundedInvoice], DEMO_FUNDING_TRANSACTION.toAddress)
      .settlementReceivedUsdc,
  ).toBe(DEMO_FUNDING_TRANSACTION.amountUsdc);
  expect(
    getDashboardSummary([fundedInvoice], "A_DIFFERENT_SUPPLIER_WALLET")
      .settlementReceivedUsdc,
  ).toBe(0);
});

test("ignores a settlement-wallet response cached for another authenticated wallet", async () => {
  getSettlementWalletMock.mockResolvedValueOnce({
    walletType: "EXTERNAL",
    address: "BzVQsk3NKMnV7dbDWMGznFovtMfnu3orPwqj3F7kmyEP",
    embeddedWalletAddress: "A_DIFFERENT_EMBEDDED_WALLET",
  });

  renderDashboard();

  await screen.findByRole("heading", { name: "Good morning, Jiyoon" });
  expect(useDevnetUsdcBalanceMock).toHaveBeenLastCalledWith(
    "8xK2f7yZQmP8Y5BwL9Vx3dTs7cR2nJ6p91Q",
  );
});
