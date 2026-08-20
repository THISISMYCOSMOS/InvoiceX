import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { DEMO_DOCUMENTS, DEMO_INVOICE } from "../../mocks/demoScenario";
import { BuyerInvoiceDetailContent } from "./BuyerInvoiceDetailPage";

test("shows the Figma verification controls for a buyer-review invoice", async () => {
  const user = userEvent.setup();
  const onConfirm = vi.fn().mockResolvedValue(undefined);
  const onReject = vi.fn().mockResolvedValue(undefined);
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
        onReject={onReject}
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
  await user.click(screen.getByRole("button", { name: "Reject invoice" }));
  expect(screen.getByText("Rejection reason")).toBeInTheDocument();
  await user.selectOptions(screen.getByRole("combobox"), "AMOUNT_ERROR");
  await user.click(screen.getByRole("button", { name: "Submit rejection" }));
  expect(onReject).toHaveBeenCalledWith("AMOUNT_ERROR", undefined);

  await user.click(screen.getByRole("button", { name: "Confirm invoice" }));
  expect(onConfirm).toHaveBeenCalledTimes(1);
  expect(await screen.findByRole("status")).toHaveTextContent("Invoice confirmation submitted.");
});

test("shows the embedded-wallet maturity-payment action for a funded invoice", async () => {
  const user = userEvent.setup();
  const onPay = vi.fn();
  render(
    <BuyerInvoiceDetailContent
      invoice={{ ...DEMO_INVOICE, status: "FUNDED" }}
      onConfirm={() => undefined}
      paymentPreparation={{
        invoiceId: DEMO_INVOICE.id,
        buyerWalletAddress: "BuyerWallet",
        settlementWalletAddress: "SettlementWallet",
        usdcMintAddress: "UsdcMint",
        amountUsdc: 3,
        amountBaseUnits: "3000000",
        decimals: 6,
        dueDate: DEMO_INVOICE.dueDate,
        transfers: [{
          recipientWalletAddress: "SettlementWallet",
          amountUsdc: 3,
          amountBaseUnits: "3000000",
        }],
        demoDueDateBypass: true,
      }}
      onPay={onPay}
    />,
  );

  expect(screen.getByRole("heading", { name: "Pay invoice amount" })).toBeInTheDocument();
  expect(screen.getByText("3 USDC")).toBeInTheDocument();
  expect(screen.getByText("SettlementWallet")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Copy address" })).not.toBeInTheDocument();
  expect(screen.queryByText("The amount, asset, and settlement address must match for automatic processing.")).not.toBeInTheDocument();
  const paymentButton = screen.getByRole("button", { name: "Pay with embedded wallet" });
  expect(paymentButton).toHaveClass("buyer-confirm-button--full");
  await user.click(paymentButton);
  expect(onPay).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("link", { name: "Download payment guide" })).not.toBeInTheDocument();
});

test("shows the detailed two-step confirmation record after buyer confirmation", () => {
  render(
    <MemoryRouter>
      <BuyerInvoiceDetailContent
        invoice={{
          ...DEMO_INVOICE,
          status: "OFFER_READY",
          verificationConfirmedAt: "2026-08-19T07:14:00.000Z",
        }}
        onConfirm={() => undefined}
      />
    </MemoryRouter>,
  );

  expect(screen.getByText("2 / 2 Buyer confirmation complete")).toBeInTheDocument();
  expect(screen.getByText("Original invoice number")).toBeInTheDocument();
  expect(screen.getByText("Transaction evidence")).toBeInTheDocument();
  expect(screen.getByText("Confirmation record")).toBeInTheDocument();
  expect(screen.getByText("Buyer Confirmed")).toBeInTheDocument();
});
