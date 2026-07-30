import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, test } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { scenarioAdapter } from "../api/client";
import { App } from "../App";

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
  expect(screen.getByText("Company & Wallet")).toBeInTheDocument();
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

test("keeps the language control first in every top-right control group", async () => {
  const { container, unmount } = renderAt("/login");
  const loginToggle = screen.getByRole("button", { name: "한국어로 전환" });

  expect(container.querySelector(".login-panel")?.firstElementChild).toBe(loginToggle);

  unmount();
  const supplier = renderAt("/supplier");
  const appToggle = await screen.findByRole("button", { name: "한국어로 전환" });

  expect(supplier.container.querySelector(".topbar__user")?.firstElementChild).toBe(appToggle);
});

test("renders the investor Figma navigation and agent decision route", async () => {
  const user = userEvent.setup();
  renderAt("/investor");

  expect(await screen.findByRole("heading", { name: "Treasury overview" })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Investor navigation" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Agent Activity" })).toHaveAttribute(
    "href",
    "/investor/activities/INV-2026-001",
  );

  await user.click(screen.getByRole("link", { name: "INV-2026-001" }));

  expect(await screen.findByRole("heading", { name: "Treasury Agent decision" })).toBeInTheDocument();
  expect(screen.getByText("6 / 6 PASSED")).toBeInTheDocument();
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
