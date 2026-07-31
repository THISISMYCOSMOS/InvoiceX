import { render, screen } from "@testing-library/react";
import {
  DEMO_AGENT_TRACES,
  DEMO_FUNDING_TRANSACTION,
  DEMO_INVESTOR_MANDATE,
  DEMO_INVOICE,
  DEMO_RISK_PASSPORT,
} from "../../mocks/demoScenario";
import { InvestorActivityContent } from "./InvestorActivityPage";

test("shows the Treasury Agent mandate decision and execution summary", () => {
  render(
    <InvestorActivityContent
      invoice={{ ...DEMO_INVOICE, riskPassport: DEMO_RISK_PASSPORT, agentTraces: DEMO_AGENT_TRACES, fundingTransaction: DEMO_FUNDING_TRANSACTION }}
      mandate={DEMO_INVESTOR_MANDATE}
      availableVaultUsdc={31_200}
    />,
  );

  expect(screen.getByRole("heading", { name: "Treasury Agent decision" })).toBeInTheDocument();
  // Every row is now a real mandate rule, so the count follows the policy.
  expect(screen.getByText("5 / 5 PASSED")).toBeInTheDocument();
  expect(screen.getAllByText("PASS")).toHaveLength(5);
  expect(screen.getByText("31,200 USDC")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Execution summary" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View RWA position" })).toHaveAttribute(
    "href",
    DEMO_FUNDING_TRANSACTION.explorerUrl,
  );
});
