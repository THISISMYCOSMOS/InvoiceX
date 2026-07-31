import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { AgentTrace } from "../../../types/agents";
import { DEMO_INVOICE, DEMO_RISK_PASSPORT } from "../../../mocks/demoScenario";
import { SupplierInvoiceDetailContent } from "../SupplierInvoiceDetailPage";

function failedTrace(summary: string): AgentTrace {
  return {
    id: "TRACE-FAILED",
    invoiceId: DEMO_INVOICE.id,
    sourceAgent: "TREASURY_AGENT",
    targetAgent: "SETTLEMENT_AGENT",
    status: "FAILED",
    summary,
    createdAt: "2026-07-31T00:00:00.000Z",
  };
}

function renderStatus(invoice: Parameters<typeof SupplierInvoiceDetailContent>[0]["invoice"]) {
  render(
    <MemoryRouter>
      <SupplierInvoiceDetailContent invoice={invoice} onAccept={() => undefined} />
    </MemoryRouter>,
  );
}

test("a blocked invoice explains itself instead of rendering an empty section", () => {
  renderStatus({
    ...DEMO_INVOICE,
    status: "BLOCKED",
    agentTraces: [failedTrace("AP2 Mandate 차단: 구매기업이 Mandate 허용 목록에 없습니다.")],
  });

  expect(screen.getByRole("heading", { name: "This invoice cannot proceed" })).toBeInTheDocument();
  expect(screen.getByText("BLOCKED")).toBeInTheDocument();
  expect(
    screen.getByText("AP2 Mandate 차단: 구매기업이 Mandate 허용 목록에 없습니다."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Early settlement was not issued. No USDC has been transferred."),
  ).toBeInTheDocument();
});

test("a blocked invoice lists the risk factors behind the refusal", () => {
  renderStatus({
    ...DEMO_INVOICE,
    status: "BLOCKED",
    riskPassport: {
      ...DEMO_RISK_PASSPORT,
      eligibility: "BLOCKED",
      riskFactors: [
        {
          severity: "HIGH",
          title: "분쟁 또는 결제 보류",
          description: "구매기업이 분쟁 또는 결제 보류가 있다고 보고했습니다.",
        },
      ],
    },
    agentTraces: [failedTrace("투자 부적격(BLOCKED)으로 조기정산 제안을 만들지 않았습니다.")],
  });

  expect(screen.getByText("분쟁 또는 결제 보류")).toBeInTheDocument();
  expect(
    screen.getByText("구매기업이 분쟁 또는 결제 보류가 있다고 보고했습니다."),
  ).toBeInTheDocument();
});

test("a revision request tells the supplier to resubmit", () => {
  renderStatus({
    ...DEMO_INVOICE,
    status: "REVISION_REQUESTED",
    agentTraces: [failedTrace("구매기업이 제출 문서의 보완을 요청했습니다.")],
  });

  expect(
    screen.getByRole("heading", { name: "The buyer asked for a correction" }),
  ).toBeInTheDocument();
  expect(screen.getByText("REVISION REQUESTED")).toBeInTheDocument();
  expect(
    screen.getByText("Correct the documents and register the invoice again."),
  ).toBeInTheDocument();
});

test("a processing error surfaces the recorded cause", () => {
  renderStatus({
    ...DEMO_INVOICE,
    status: "ERROR",
    agentTraces: [failedTrace("서버 재시작으로 DOCUMENT_ANALYZING 처리가 중단되었습니다.")],
  });

  expect(
    screen.getByRole("heading", { name: "Processing stopped unexpectedly" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText("서버 재시작으로 DOCUMENT_ANALYZING 처리가 중단되었습니다."),
  ).toBeInTheDocument();
});

test("every exception screen offers a way forward", () => {
  renderStatus({ ...DEMO_INVOICE, status: "BLOCKED" });

  expect(screen.getByRole("link", { name: "Back to invoices" })).toHaveAttribute(
    "href",
    "/supplier",
  );
  expect(screen.getByRole("link", { name: "Register a new invoice" })).toHaveAttribute(
    "href",
    "/supplier/invoices/new",
  );
});
