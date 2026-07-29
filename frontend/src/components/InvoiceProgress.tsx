import { getSupplierRegistrationStep, type InvoiceStatus } from "../types/invoice";

export function InvoiceProgress({ status }: { status: InvoiceStatus }) {
  const current = getSupplierRegistrationStep(status);
  return <ol aria-label="공급기업 등록 단계">{["REGISTER", "BUYER_REVIEW", "VERIFIED"].map((step) => <li key={step} aria-current={current === step ? "step" : undefined}>{step === "REGISTER" ? "등록" : step === "BUYER_REVIEW" ? "구매기업 확인" : "검증 완료"}</li>)}</ol>;
}
