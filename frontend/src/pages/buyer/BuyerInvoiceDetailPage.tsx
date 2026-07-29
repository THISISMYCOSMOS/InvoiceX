import { useState } from "react";
import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { useBuyerConfirm } from "../../hooks/useBuyerConfirm";
import { useInvoice } from "../../hooks/useInvoice";
import type { Invoice } from "../../types/invoice";

export function BuyerInvoiceDetailContent({ invoice, onConfirm }: { invoice: Invoice; onConfirm: () => void }) {
  const [message, setMessage] = useState<string>();
  if (invoice.status === "BUYER_REVIEW") {
    return <section><h1>{invoice.id}</h1><StatusBadge status={invoice.status} /><h2>검증 요청</h2><dl><dt>실제 거래 여부</dt><dd>확인 필요</dd><dt>인보이스 금액</dt><dd>{invoice.invoiceAmountKrw.toLocaleString()} KRW</dd><dt>만기일</dt><dd>{invoice.dueDate}</dd><dt>납품·용역 완료 여부</dt><dd>확인 필요</dd><dt>분쟁 또는 지급 보류 사유</dt><dd>없음</dd></dl><button type="button" onClick={onConfirm}>확인 완료</button><button type="button" onClick={() => setMessage("보완 요청 상태로 전환할 수 있습니다.")}>보완 요청</button><button type="button" onClick={() => setMessage("이의 제기 상태로 전환할 수 있습니다.")}>이의 제기</button>{message && <p role="status">{message}</p>}</section>;
  }
  return <section><h1>{invoice.id}</h1><StatusBadge status={invoice.status} /><h2>만기 지급 상태</h2><p>지급 예정 원화 금액: {invoice.invoiceAmountKrw.toLocaleString()} KRW</p><p>지급 기한: {invoice.dueDate}</p><p>Mock 정산 파트너 이벤트를 통해 입금·온체인 정산을 진행합니다.</p></section>;
}

export function BuyerInvoiceDetailPage() {
  const { invoiceId = "" } = useParams();
  const invoice = useInvoice(invoiceId);
  const confirm = useBuyerConfirm();
  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) return <ErrorState error={invoice.error ?? new Error("인보이스를 찾을 수 없습니다.")} />;
  return <BuyerInvoiceDetailContent invoice={invoice.data} onConfirm={() => invoice.data.verificationId && confirm.mutate(invoice.data.verificationId)} />;
}
