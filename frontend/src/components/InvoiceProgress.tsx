import { getSupplierRegistrationStep, type InvoiceStatus } from "../types/invoice";
import { useLanguage } from "../i18n/LanguageContext";

export function InvoiceProgress({ status }: { status: InvoiceStatus }) {
  const { t } = useLanguage();
  const current = getSupplierRegistrationStep(status);
  const steps = ["REGISTER", "BUYER_REVIEW", "VERIFIED"] as const;

  return (
    <ol className="invoice-progress" aria-label={t("Supplier registration progress", "공급기업 등록 단계")}>
      {steps.map((step, index) => {
        const isComplete = steps.indexOf(current) > index;
        const label = step === "REGISTER"
          ? t("Registered", "등록")
          : step === "BUYER_REVIEW"
            ? t("Buyer verification", "구매기업 확인")
            : t("Verified", "검증 완료");

        return (
          <li
            key={step}
            className={isComplete ? "is-complete" : current === step ? "is-current" : ""}
            aria-current={current === step ? "step" : undefined}
          >
            <span className="invoice-progress__number">{isComplete ? "✓" : index + 1}</span>
            <span>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
