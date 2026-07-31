import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, test } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { scenarioAdapter } from "../api/client";
import { App } from "../App";
import { DEMO_INVOICE } from "../mocks/demoScenario";

beforeEach(async () => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  await scenarioAdapter.reset();
});

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}

test.each([
  ["/supplier", "Good morning, Minjun"],
  ["/supplier/company-wallet", "Company & Wallet"],
  ["/buyer", "Invoice verification"],
  ["/investor", "Treasury overview"],
  ["/dev/demo", "Developer demo controls"],
])("renders %s", async (path, expectedText) => {
  renderAt(path);

  expect(await screen.findByRole("heading", { name: expectedText })).toBeInTheDocument();
});

test("renders the Figma login form", () => {
  renderAt("/login");

  expect(screen.getByRole("heading", { name: "Sign in to InvoiceX" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Supplier" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Buyer" })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("button", { name: "Investor" })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByLabelText("Company email")).toBeInTheDocument();
  expect(screen.getByLabelText("Password")).toBeInTheDocument();
});

test.each([
  ["Supplier", "supplier@company.com", "supplier", "Good morning, Minjun"],
  ["Buyer", "buyer@company.com", "buyer", "Invoice verification"],
  ["Investor", "investor@company.com", "investor", "Treasury overview"],
])("signs the %s demo account into its dashboard", async (role, email, password, expectedText) => {
  const user = userEvent.setup();
  renderAt("/login");

  await user.click(screen.getByRole("button", { name: role }));
  await user.type(screen.getByLabelText("Company email"), email);
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByRole("heading", { name: expectedText })).toBeInTheDocument();
});

test("rejects credentials that do not match the selected role", async () => {
  const user = userEvent.setup();
  renderAt("/login");

  await user.type(screen.getByLabelText("Company email"), "buyer@company.com");
  await user.type(screen.getByLabelText("Password"), "buyer");
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  expect(screen.getByRole("alert")).toHaveTextContent("Check the selected role, email, and password.");
  expect(screen.getByRole("heading", { name: "Sign in to InvoiceX" })).toBeInTheDocument();
});

test("renders supplier navigation in the shared application shell", async () => {
  renderAt("/supplier");

  expect(await screen.findByRole("navigation", { name: "Supplier navigation" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/supplier");
  expect(screen.getByRole("link", { name: "Invoices" })).toHaveAttribute("href", "/supplier/invoices/new");
  expect(screen.getByRole("link", { name: "Company & Wallet" })).toHaveAttribute("href", "/supplier/company-wallet");
});

test("shows company details and manages the supplier demo wallet", async () => {
  const user = userEvent.setup();
  const { container } = renderAt("/supplier/company-wallet");

  expect(await screen.findByRole("heading", { name: "Company & Wallet" })).toBeInTheDocument();
  expect(screen.getByText("Alpha Components Co., Ltd.")).toBeInTheDocument();
  // The settlement wallet must be the address the server actually pays out to.
  expect(screen.getByText(DEMO_INVOICE.supplier.walletAddress!)).toBeInTheDocument();
  expect(container.querySelector(".topbar .wallet-label")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Disconnect wallet" }));
  expect(screen.getByRole("heading", { name: "Connect a settlement wallet" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Connect wallet" }));
  expect(screen.getByRole("button", { name: "Disconnect wallet" })).toBeInTheDocument();
});

test("switches between English and Korean from login and keeps the choice across routes", async () => {
  const user = userEvent.setup();
  const { unmount } = renderAt("/login");

  await user.click(screen.getByRole("button", { name: "한국어로 전환" }));

  expect(screen.getByRole("heading", { name: "InvoiceX에 로그인" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Switch to English" })).toBeInTheDocument();
  expect(document.documentElement).toHaveAttribute("lang", "ko");

  unmount();
  renderAt("/supplier");

  expect(await screen.findByRole("heading", { name: "좋은 아침이에요, 민준님" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "개요" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Switch to English" })).toBeInTheDocument();
});

test("places the role switcher before the language control in the app topbar", async () => {
  const { container, unmount } = renderAt("/login");
  const loginToggle = screen.getByRole("button", { name: "한국어로 전환" });

  expect(container.querySelector(".login-panel")?.firstElementChild).toBe(loginToggle);

  unmount();
  const supplier = renderAt("/supplier");
  const appToggle = await screen.findByRole("button", { name: "한국어로 전환" });
  const roleSwitcher = screen.getByRole("combobox", { name: "Switch role" });

  expect(supplier.container.querySelector(".topbar__user")?.firstElementChild).toContainElement(roleSwitcher);
  expect(roleSwitcher.parentElement?.nextElementSibling).toBe(appToggle);
});

test("switches demo roles from the topbar dropdown", async () => {
  const user = userEvent.setup();
  renderAt("/supplier");

  const roleSwitcher = await screen.findByRole("combobox", { name: "Switch role" });
  await user.selectOptions(roleSwitcher, "BUYER");

  expect(await screen.findByRole("heading", { name: "Invoice verification" })).toBeInTheDocument();
  expect(roleSwitcher).toHaveValue("BUYER");
});

test("renders the investor Figma navigation and agent decision route", async () => {
  const user = userEvent.setup();
  renderAt("/investor");

  expect(await screen.findByRole("heading", { name: "Treasury overview" })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Investor navigation" })).toBeInTheDocument();
  expect(screen.queryByText("Vault · 7VB...0Qe")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Agent Activity" })).toHaveAttribute(
    "href",
    "/investor/activities/INV-2026-001",
  );
  expect(screen.queryByText("Settlement Reports")).not.toBeInTheDocument();

  await user.click(screen.getByRole("link", { name: "INV-2026-001" }));

  expect(await screen.findByRole("heading", { name: "Treasury Agent decision" })).toBeInTheDocument();
  // The pass count now follows the live mandate evaluation, so this routing
  // smoke test only checks that the policy card rendered.
  expect(screen.getByText(/\d+ \/ \d+ PASSED/)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Mandate evaluation/ })).toBeInTheDocument();
});

test("returns from buyer verification to the buyer dashboard", async () => {
  const user = userEvent.setup();
  renderAt("/buyer/invoices/INV-2026-001?section=verification");

  const backLink = await screen.findByRole("link", { name: "Back" });
  expect(backLink).toHaveAttribute("href", "/buyer");

  await user.click(backLink);
  expect(await screen.findByRole("heading", { name: "Invoice verification" })).toBeInTheDocument();
});

test("opens a due invoice from the buyer dashboard payment queue", async () => {
  const user = userEvent.setup();
  renderAt("/buyer");

  expect(await screen.findByRole("heading", { name: "Payments due soon" })).toBeInTheDocument();
  expect(screen.queryByText("Completed")).not.toBeInTheDocument();
  const paymentLink = screen.getByRole("link", { name: "Pay INV-2026-001" });
  expect(paymentLink).toHaveAttribute("href", "/buyer/invoices/INV-2026-001?section=payment");

  await user.click(paymentLink);
  expect(await screen.findByRole("heading", { name: "Pay invoice amount" })).toBeInTheDocument();
});

test("translates buyer and investor screens into Korean", async () => {
  const user = userEvent.setup();
  const buyer = renderAt("/buyer");

  await screen.findByRole("heading", { name: "Invoice verification" });
  await user.click(screen.getByRole("button", { name: "한국어로 전환" }));

  expect(screen.getByRole("heading", { name: "인보이스 확인" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "확인 요청" })).toBeInTheDocument();

  buyer.unmount();
  renderAt("/investor");

  expect(await screen.findByRole("heading", { name: "자금 운용 현황" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "에이전트 활동" })).toBeInTheDocument();
});
