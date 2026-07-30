import { useState } from "react";
import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { useBuyerConfirm } from "../../hooks/useBuyerConfirm";
import { useInvoice } from "../../hooks/useInvoice";
import type { Invoice } from "../../types/invoice";
import { useLanguage } from "../../i18n/LanguageContext";

export function BuyerInvoiceDetailContent({ invoice, onConfirm }: { invoice: Invoice; onConfirm: () => void }) {
  const [message, setMessage] = useState<string>();
  const { t } = useLanguage();
  if (invoice.status === "BUYER_REVIEW") {
    return <section><h1>{invoice.id}</h1><StatusBadge status={invoice.status} /><h2>{t("Verification request", "검증 요청")}</h2><dl><dt>{t("Transaction authenticity", "실제 거래 여부")}</dt><dd>{t("Review required", "확인 필요")}</dd><dt>{t("Invoice amount", "인보이스 금액")}</dt><dd>{invoice.invoiceAmountKrw.toLocaleString()} KRW</dd><dt>{t("Due date", "만기일")}</dt><dd>{invoice.dueDate}</dd><dt>{t("Delivery or service completion", "납품·용역 완료 여부")}</dt><dd>{t("Review required", "확인 필요")}</dd><dt>{t("Dispute or payment hold reason", "분쟁 또는 지급 보류 사유")}</dt><dd>{t("None", "없음")}</dd></dl><button type="button" onClick={onConfirm}>{t("Confirm", "확인 완료")}</button><button type="button" onClick={() => setMessage(t("You can move this invoice to a change-request state.", "보완 요청 상태로 전환할 수 있습니다."))}>{t("Request changes", "보완 요청")}</button><button type="button" onClick={() => setMessage(t("You can move this invoice to a dispute state.", "이의 제기 상태로 전환할 수 있습니다."))}>{t("Raise dispute", "이의 제기")}</button>{message && <p role="status">{message}</p>}</section>;
  }
  return <section><h1>{invoice.id}</h1><StatusBadge status={invoice.status} /><h2>{t("Maturity payment status", "만기 지급 상태")}</h2><p>{t("Scheduled KRW payment", "지급 예정 원화 금액")}: {invoice.invoiceAmountKrw.toLocaleString()} KRW</p><p>{t("Payment due date", "지급 기한")}: {invoice.dueDate}</p><p>{t("Payment and on-chain settlement proceed through a mock settlement-partner event.", "Mock 정산 파트너 이벤트를 통해 입금·온체인 정산을 진행합니다.")}</p></section>;
}

export function BuyerInvoiceDetailPage() {
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const invoice = useInvoice(invoiceId);
  const confirm = useBuyerConfirm();
  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) return <ErrorState error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))} />;
  return <BuyerInvoiceDetailContent invoice={invoice.data} onConfirm={() => invoice.data.verificationId && confirm.mutate(invoice.data.verificationId)} />;
}
