import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { InvoiceProgress } from "../../components/InvoiceProgress";
import { LoadingState } from "../../components/LoadingState";
import { useAcceptOffer } from "../../hooks/useAcceptOffer";
import { useInvoice } from "../../hooks/useInvoice";
import { useRequestVerification } from "../../hooks/useRequestVerification";
import type { Invoice } from "../../types/invoice";
import { BuyerReviewPendingSection } from "./sections/BuyerReviewPendingSection";
import { DocumentReviewSection } from "./sections/DocumentReviewSection";
import { EarlySettlementOfferSection } from "./sections/EarlySettlementOfferSection";
import { FundingProgressSection } from "./sections/FundingProgressSection";
import { FundingReceiptSection } from "./sections/FundingReceiptSection";
import { InvoiceWorkflowStatusSection } from "./sections/InvoiceWorkflowStatusSection";
import { RwaIssuedSection } from "./sections/RwaIssuedSection";
import { SettlementReceiptSection } from "./sections/SettlementReceiptSection";
import { useLanguage } from "../../i18n/LanguageContext";
import { useAgentActivity } from "../../hooks/useAgentActivity";
import { AgentActivityTimeline } from "../../components/AgentActivityTimeline";

export function SupplierInvoiceDetailContent({
  invoice,
  onAccept,
  isAccepting = false,
  acceptError,
  onRequestVerification = () => undefined,
  isRequestingVerification = false,
}: {
  invoice: Invoice;
  onAccept: () => void;
  isAccepting?: boolean;
  acceptError?: string;
  onRequestVerification?: () => void;
  isRequestingVerification?: boolean;
}) {
  const renderContent = () => {
    if (invoice.status === "DOCUMENT_REVIEW_REQUIRED") {
      return (
        <DocumentReviewSection
          invoice={invoice}
          onConfirm={onRequestVerification}
          isPending={isRequestingVerification}
        />
      );
    }

    if (invoice.status === "BUYER_REVIEW") {
      return <BuyerReviewPendingSection invoice={invoice} />;
    }

    if (invoice.status === "OFFER_READY") {
      return (
        <EarlySettlementOfferSection
          invoice={invoice}
          onAccept={onAccept}
          isRequesting={isAccepting}
          requestError={acceptError}
        />
      );
    }

    if (invoice.status === "RWA_ISSUED") {
      return <RwaIssuedSection invoice={invoice} />;
    }

    if (invoice.status === "FUNDING") {
      return <FundingProgressSection invoice={invoice} />;
    }

    if (invoice.status === "FUNDED") {
      return <FundingReceiptSection invoice={invoice} />;
    }

    if (invoice.status === "SETTLED") {
      return <SettlementReceiptSection invoice={invoice} />;
    }

    return <InvoiceWorkflowStatusSection invoice={invoice} />;
  };

  if (invoice.status === "DOCUMENT_REVIEW_REQUIRED") {
    return renderContent();
  }

  return (
    <div className="supplier-invoice-workflow">
      {invoice.status !== "BUYER_REVIEW" && <InvoiceProgress status={invoice.status} />}
      {renderContent()}
    </div>
  );
}

export function SupplierInvoiceDetailPage() {
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const invoice = useInvoice(invoiceId);
  const acceptOffer = useAcceptOffer();
  const requestVerification = useRequestVerification();
  const activity = useAgentActivity(invoiceId, "Supplier");
  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) return <ErrorState error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))} />;
  return (
    <><SupplierInvoiceDetailContent
      invoice={invoice.data}
      onAccept={() => acceptOffer.mutate({ invoiceId: invoice.data.id, response: "ACCEPT" })}
      isAccepting={acceptOffer.isPending}
      acceptError={acceptOffer.error instanceof Error ? acceptOffer.error.message : undefined}
      onRequestVerification={() => requestVerification.mutate(invoice.data.id)}
      isRequestingVerification={requestVerification.isPending}
    /><AgentActivityTimeline activity={activity.data} /></>
  );
}
