import { render, screen } from "@testing-library/react";
import { DEMO_AGENT_TRACES, DEMO_FUNDING_TRANSACTION, DEMO_INVOICE, DEMO_RISK_PASSPORT } from "../../mocks/demoScenario";
import { InvestorActivityContent } from "./InvestorActivityPage";

test("shows the Treasury Agent mandate decision and execution summary", () => {
  render(<InvestorActivityContent invoice={{ ...DEMO_INVOICE, riskPassport: DEMO_RISK_PASSPORT, agentTraces: DEMO_AGENT_TRACES, fundingTransaction: DEMO_FUNDING_TRANSACTION }} />);

  expect(screen.getByRole("heading", { name: "Treasury Agent decision" })).toBeInTheDocument();
  expect(screen.getByText("6 / 6 PASSED")).toBeInTheDocument();
  expect(screen.getAllByText("PASS")).toHaveLength(6);
  expect(screen.getByRole("heading", { name: "Execution summary" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View RWA position" })).toHaveAttribute(
    "href",
    DEMO_FUNDING_TRANSACTION.explorerUrl,
  );
});
