import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { DEMO_DOCUMENTS, DEMO_INVOICE } from "../../mocks/demoScenario";
import { BuyerInvoiceDetailContent } from "./BuyerInvoiceDetailPage";

test("shows the Figma verification controls for a buyer-review invoice", async () => {
  const user = userEvent.setup();
  const onConfirm = vi.fn().mockResolvedValue(undefined);
  render(
    <MemoryRouter>
      <BuyerInvoiceDetailContent
        invoice={{
          ...DEMO_INVOICE,
          status: "BUYER_REVIEW",
          verificationId: "VER-2026-001",
          verificationRequestedAt: "2026-08-03T19:22:08.000Z",
          documents: DEMO_DOCUMENTS.map((document) => ({
            ...document,
            storageUrl: `https://storage.example.test/${document.fileName}`,
          })),
        }}
        onConfirm={onConfirm}
      />
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: "Verify invoice INV-2026-001" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Invoice" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByTitle("01_Invoice_INV-2026-001.pdf")).toHaveAttribute(
    "src",
    "https://storage.example.test/01_Invoice_INV-2026-001.pdf",
  );
  expect(screen.getByText(/^Requested /)).toBeInTheDocument();
  expect(screen.getByText("Transaction exists")).toBeInTheDocument();
  expect(screen.getByText("Supplier information")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Request revision" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Confirm invoice" }));
  expect(onConfirm).toHaveBeenCalledTimes(1);
  expect(await screen.findByRole("status")).toHaveTextContent("Invoice confirmation submitted.");
});

test("shows the Figma maturity-payment screen for a funded invoice", () => {
  render(
    <BuyerInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "FUNDED" }}
      onConfirm={() => undefined}
    />,
  );

  expect(screen.getByRole("heading", { name: "Pay invoice amount" })).toBeInTheDocument();
  expect(screen.getByText("₩3,000")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Copy account number" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Download payment guide" })).not.toBeInTheDocument();
});
