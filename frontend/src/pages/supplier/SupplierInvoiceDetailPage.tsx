import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { InvoiceProgress } from "../../components/InvoiceProgress";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { useAcceptOffer } from "../../hooks/useAcceptOffer";
import { useInvoice } from "../../hooks/useInvoice";
import type { Invoice } from "../../types/invoice";
import { BuyerReviewPendingSection } from "./sections/BuyerReviewPendingSection";
import { EarlySettlementOfferSection } from "./sections/EarlySettlementOfferSection";
import { FundingProgressSection } from "./sections/FundingProgressSection";
import { FundingReceiptSection } from "./sections/FundingReceiptSection";
import { SettlementReceiptSection } from "./sections/SettlementReceiptSection";

export function SupplierInvoiceDetailContent({ invoice, onAccept }: { invoice: Invoice; onAccept: () => void }) {
  let section = <section><h2>{invoice.status === "DOCUMENT_REVIEW_REQUIRED" ? "분석 결과 확인" : "인보이스 진행 상태"}</h2></section>;
  if (invoice.status === "BUYER_REVIEW") section = <BuyerReviewPendingSection />;
  if (invoice.status === "OFFER_READY") section = <EarlySettlementOfferSection invoice={invoice} onAccept={onAccept} />;
  if (invoice.status === "FUNDING") section = <FundingProgressSection />;
  if (invoice.status === "FUNDED") section = <FundingReceiptSection invoice={invoice} />;
  if (invoice.status === "SETTLED") section = <SettlementReceiptSection invoice={invoice} />;
  return <><h1>{invoice.id}</h1><StatusBadge status={invoice.status} /><InvoiceProgress status={invoice.status} />{section}</>;
}

export function SupplierInvoiceDetailPage() {
  const { invoiceId = "" } = useParams();
  const invoice = useInvoice(invoiceId);
  const acceptOffer = useAcceptOffer();
  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) return <ErrorState error={invoice.error ?? new Error("인보이스를 찾을 수 없습니다.")} />;
  return <SupplierInvoiceDetailContent invoice={invoice.data} onAccept={() => acceptOffer.mutate({ invoiceId: invoice.data.id, response: "ACCEPT" })} />;
}
