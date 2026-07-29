import { getInvoiceStatusLabel, getSupplierRegistrationStep } from "./invoice";

test("maps buyer review to the supplier buyer-review step", () => {
  expect(getSupplierRegistrationStep("BUYER_REVIEW")).toBe("BUYER_REVIEW");
  expect(getInvoiceStatusLabel("FUNDED")).toBe("USDC 지급 완료");
});
