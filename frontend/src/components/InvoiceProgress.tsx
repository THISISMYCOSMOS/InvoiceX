import { getSupplierRegistrationStep, type InvoiceStatus } from "../types/invoice";
import { useLanguage } from "../i18n/LanguageContext";

export function InvoiceProgress({ status }: { status: InvoiceStatus }) {
  const { t } = useLanguage();
  const current = getSupplierRegistrationStep(status);
  return <ol aria-label={t("Supplier registration progress", "공급기업 등록 단계")}>{["REGISTER", "BUYER_REVIEW", "VERIFIED"].map((step) => <li key={step} aria-current={current === step ? "step" : undefined}>{step === "REGISTER" ? t("Registered", "등록") : step === "BUYER_REVIEW" ? t("Buyer verification", "구매기업 확인") : t("Verified", "검증 완료")}</li>)}</ol>;
}
