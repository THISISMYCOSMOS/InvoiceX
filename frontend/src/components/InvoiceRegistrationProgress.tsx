import { useLanguage } from "../i18n/LanguageContext";

type InvoiceRegistrationStep = 1 | 2 | 3;

const stepLabels: Record<InvoiceRegistrationStep, [string, string]> = {
  1: ["Upload documents", "문서 업로드"],
  2: ["Review extraction", "추출 정보 확인"],
  3: ["Buyer review requested", "구매기업 검토 요청"],
};

export function InvoiceRegistrationProgress({ step }: { step: InvoiceRegistrationStep }) {
  const { t } = useLanguage();
  const [englishLabel, koreanLabel] = stepLabels[step];

  return (
    <div className="review-progress" aria-label={t("Invoice registration progress", "인보이스 등록 진행 상황")}>
      <div className="review-progress__summary">
        <strong aria-current="step">{t(`${step} / 3 ${englishLabel}`, `${step} / 3 ${koreanLabel}`)}</strong>
        <span>{t("Invoice verification", "인보이스 확인")}</span>
      </div>
      <div className="review-progress__track" aria-hidden="true">
        <span style={{ width: `${(step / 3) * 100}%` }} />
      </div>
    </div>
  );
}
