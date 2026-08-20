import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DEMO_AGENT_TRACES, DEMO_FUNDING_TRANSACTION, DEMO_INVOICE, DEMO_RISK_PASSPORT, DEMO_RWA_ASSET } from "../../mocks/demoScenario";
import { InvestorActivityContent } from "./InvestorActivityPage";

test("shows the Treasury Agent mandate decision and execution summary", () => {
  render(<InvestorActivityContent invoice={{
    ...DEMO_INVOICE,
    riskPassport: DEMO_RISK_PASSPORT,
    agentTraces: DEMO_AGENT_TRACES,
    fundingTransaction: DEMO_FUNDING_TRANSACTION,
    rwaAsset: { ...DEMO_RWA_ASSET, status: "SOLD", purchaseTransaction: DEMO_FUNDING_TRANSACTION },
    agentDecision: {
      invoiceId: DEMO_INVOICE.id,
      status: "EXECUTED",
      checks: { policyActive: true, buyerAllowlist: true },
      amountUsdc: DEMO_FUNDING_TRANSACTION.amountUsdc,
      amountBaseUnits: DEMO_FUNDING_TRANSACTION.amountBaseUnits,
      createdAt: DEMO_FUNDING_TRANSACTION.createdAt,
    },
  }} />);

  expect(screen.getByRole("heading", { name: "Treasury Agent decision" })).toBeInTheDocument();
  expect(screen.getByText("2 / 2 PASSED")).toBeInTheDocument();
  expect(screen.getAllByText("PASS")).toHaveLength(2);
  expect(screen.getByRole("heading", { name: "Execution summary" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View RWA position" })).toHaveAttribute(
    "href",
    DEMO_FUNDING_TRANSACTION.explorerUrl,
  );
});

test("moves detailed agent events into a dedicated timeline tab", async () => {
  const user = userEvent.setup();
  render(<InvestorActivityContent invoice={DEMO_INVOICE} activity={{
    invoiceId: DEMO_INVOICE.id,
    role: "Investor",
    runs: [],
    timeline: [{
      id: "activity-1",
      kind: "TOOL",
      status: "COMPLETED",
      title: "evaluate_mandate",
      summary: "The signed investment policy was evaluated successfully.",
      createdAt: "2026-08-21T09:00:00Z",
      methodVersion: "risk-rules-v2",
      checks: { policyActive: true, buyerAllowlist: true },
    }],
  }} />);

  await user.click(screen.getByRole("tab", { name: "Agent timeline" }));

  expect(screen.getByRole("heading", { name: "Execution timeline" })).toBeInTheDocument();
  expect(screen.getByText("evaluate_mandate")).toBeInTheDocument();
  expect(screen.getByText("policyActive: PASS")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Execution summary" })).not.toBeInTheDocument();
});
