import { render, screen } from "@testing-library/react";
import { DEMO_AGENT_TRACES, DEMO_FUNDING_TRANSACTION, DEMO_INVOICE, DEMO_RISK_PASSPORT } from "../../mocks/demoScenario";
import { InvestorActivityContent } from "./InvestorActivityPage";

test("shows Agent Trace and transaction data for the investor activity", () => {
  render(<InvestorActivityContent invoice={{ ...DEMO_INVOICE, riskPassport: DEMO_RISK_PASSPORT, agentTraces: DEMO_AGENT_TRACES, fundingTransaction: DEMO_FUNDING_TRANSACTION }} />);

  expect(screen.getByText("RISK AGENT → TREASURY AGENT")).toBeInTheDocument();
  expect(screen.getByText("Transaction Hash")).toBeInTheDocument();
});
