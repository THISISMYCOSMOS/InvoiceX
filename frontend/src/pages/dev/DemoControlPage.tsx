import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { useDemoControl } from "../../hooks/useDemoControl";
import { useInvoice } from "../../hooks/useInvoice";
import type { InvoiceStatus } from "../../types/invoice";
import { useLanguage } from "../../i18n/LanguageContext";

const invoiceId = "INV-2026-001";

function enabled(status: InvoiceStatus, allowed: InvoiceStatus[]) {
  return allowed.includes(status);
}

export function DemoControlPage() {
  const invoice = useInvoice(invoiceId);
  const controls = useDemoControl();
  const { t } = useLanguage();
  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) return <ErrorState error={invoice.error ?? new Error(t("Demo data not found.", "데모 데이터를 찾을 수 없습니다."))} />;
  const current = invoice.data;
  const anyPending = Object.values(controls).some((control) => control.isPending);
  const anyError = Object.values(controls).find((control) => control.error)?.error;

  return <section><h1>{t("Developer demo controls", "개발자 데모 제어")}</h1><p>{t("This screen is hidden from regular user navigation.", "이 화면은 일반 사용자용 내비게이션에 표시하지 않습니다.")}</p><StatusBadge status={current.status} /><div><button type="button" disabled={anyPending} onClick={() => controls.reset.mutate()}>{t("Reset all demo data", "전체 데모 데이터 초기화")}</button><button type="button" disabled={anyPending || !enabled(current.status, ["DRAFT", "DOCUMENT_UPLOADING"])} onClick={() => controls.analyze.mutate(invoiceId)}>{t("Run Document Agent analysis", "Document Agent 분석 실행")}</button><button type="button" disabled={anyPending || !enabled(current.status, ["DOCUMENT_REVIEW_REQUIRED", "BUYER_REVIEW"])} onClick={() => controls.confirm.mutate(invoiceId)}>Buyer Confirm</button><button type="button" disabled={anyPending || current.status !== "OFFER_READY"} onClick={() => controls.generateRiskPassport.mutate(invoiceId)}>{t("Generate Risk Passport", "Risk Passport 생성")}</button><button type="button" disabled={anyPending || current.status !== "OFFER_READY"} onClick={() => controls.acceptOffer.mutate(invoiceId)}>{t("Accept supplier terms", "공급기업 조건 동의")}</button><button type="button" disabled={anyPending || current.status !== "FUNDED"} onClick={() => controls.mockPayment.mutate(invoiceId)}>{t("Trigger mock USDC payment", "USDC 입금 Mock 이벤트 발생")}</button><button type="button" disabled={anyPending || current.status !== "SETTLING"} onClick={() => controls.settle.mutate(invoiceId)}>{t("Run Settlement", "Settlement 실행")}</button></div>{current.riskPassport && <p>{t("Risk Passport was generated automatically after Buyer Confirm.", "Risk Passport는 Buyer Confirm 시 자동 생성되었습니다.")}</p>}{anyError && <ErrorState error={anyError} />}</section>;
}
