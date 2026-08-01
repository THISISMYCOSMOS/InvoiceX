import { getInvoiceStatusLabel, getSupplierRegistrationStep } from "./invoice";

test("maps buyer review to the supplier buyer-review step", () => {
  expect(getSupplierRegistrationStep("BUYER_REVIEW")).toBe("BUYER_REVIEW");
  expect(getInvoiceStatusLabel("RWA_ISSUED")).toBe("RWA 발행 완료 · Agent 자동 투자 처리 중");
  expect(getInvoiceStatusLabel("FUNDED")).toBe("USDC 지급 완료");
});
