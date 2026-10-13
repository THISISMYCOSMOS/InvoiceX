import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { InvoiceProgress } from "../../components/InvoiceProgress";
import { LoadingState } from "../../components/LoadingState";
import { useAcceptOffer } from "../../hooks/useAcceptOffer";
import { useInvoice } from "../../hooks/useInvoice";
import { useRequestVerification } from "../../hooks/useRequestVerification";
import { useRequestRiskReview } from "../../hooks/useRequestRiskReview";
import type { Invoice } from "../../types/invoice";
import { BuyerReviewPendingSection } from "./sections/BuyerReviewPendingSection";
import { DocumentReviewSection } from "./sections/DocumentReviewSection";
import { EarlySettlementOfferSection, type OfferStage } from "./sections/EarlySettlementOfferSection";
import { FundingProgressSection } from "./sections/FundingProgressSection";
import { FundingReceiptSection } from "./sections/FundingReceiptSection";
import { InvoiceWorkflowStatusSection } from "./sections/InvoiceWorkflowStatusSection";
import { RwaIssuedSection } from "./sections/RwaIssuedSection";
import { SettlementReceiptSection } from "./sections/SettlementReceiptSection";
import { useLanguage } from "../../i18n/LanguageContext";

export function SupplierInvoiceDetailContent({
  invoice,
  onAccept,
  isAccepting = false,
  acceptError,
  onRequestVerification = () => undefined,
  onEditDocuments = () => undefined,
  isRequestingVerification = false,
  onRequestRiskReview = () => undefined,
  isRequestingRiskReview = false,
  riskReviewError,
}: {
  invoice: Invoice;
  onAccept: () => void;
  isAccepting?: boolean;
  acceptError?: string;
  onRequestVerification?: () => void;
  onEditDocuments?: () => void;
  isRequestingVerification?: boolean;
  onRequestRiskReview?: () => void;
  isRequestingRiskReview?: boolean;
  riskReviewError?: string;
}) {
  const { t } = useLanguage();
  const [offerStage, setOfferStage] = useState<OfferStage>("risk");
  const [isRiskReviewNoticeOpen, setRiskReviewNoticeOpen] = useState(invoice.status === "REVIEW_REQUESTED");

  useEffect(() => {
    if (invoice.status === "REVIEW_REQUESTED") setRiskReviewNoticeOpen(true);
  }, [invoice.status]);

  const renderContent = () => {
    if (invoice.status === "DOCUMENT_REVIEW_REQUIRED") {
      return (
        <DocumentReviewSection
          invoice={invoice}
          onConfirm={onRequestVerification}
          onEditDocuments={onEditDocuments}
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
          stage={offerStage}
          onStageChange={setOfferStage}
          onAccept={onAccept}
          isRequesting={isAccepting}
          requestError={acceptError}
          onRequestRiskReview={onRequestRiskReview}
          isRequestingRiskReview={isRequestingRiskReview}
          riskReviewError={riskReviewError}
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

    return (
      <InvoiceWorkflowStatusSection
        invoice={invoice}
        onRequestReview={onRequestRiskReview}
        isRequestingReview={isRequestingRiskReview}
        reviewError={riskReviewError}
      />
    );
  };

  const riskReviewNotice = isRiskReviewNoticeOpen ? (
    <div className="risk-review-modal" role="dialog" aria-modal="true" aria-labelledby="risk-review-modal-title">
      <section className="risk-review-modal__card">
        <span className="offer-ready-chip">REVIEW REQUESTED</span>
        <h2 id="risk-review-modal-title">{t("Risk Score review requested", "Risk Score 이의 신청이 접수되었습니다")}</h2>
        <p>{t("The invoice workflow is paused while the submitted Risk Score is reviewed.", "제출한 Risk Score를 검토하는 동안 인보이스 진행이 일시 중지됩니다.")}</p>
        <button type="button" className="primary-button" onClick={() => setRiskReviewNoticeOpen(false)}>{t("Close", "확인")}</button>
      </section>
    </div>
  ) : null;

  if (invoice.status === "DOCUMENT_REVIEW_REQUIRED") {
    return <>{renderContent()}{riskReviewNotice}</>;
  }

  return (
    <>
      <div className="supplier-invoice-workflow">
        {invoice.status !== "BUYER_REVIEW" && invoice.status !== "FUNDED" && (
          <InvoiceProgress status={invoice.status} offerStage={offerStage} />
        )}
        {renderContent()}
      </div>
      {riskReviewNotice}
    </>
  );
}

export function SupplierInvoiceDetailPage() {
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const navigate = useNavigate();
  const invoice = useInvoice(invoiceId);
  const acceptOffer = useAcceptOffer();
  const requestVerification = useRequestVerification();
  const requestRiskReview = useRequestRiskReview();
  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) return <ErrorState error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))} />;
  return (
    <SupplierInvoiceDetailContent
      invoice={invoice.data}
      onAccept={() => acceptOffer.mutate({ invoiceId: invoice.data.id, response: "ACCEPT" })}
      isAccepting={acceptOffer.isPending}
      acceptError={acceptOffer.error instanceof Error ? acceptOffer.error.message : undefined}
      onRequestVerification={() => requestVerification.mutate(invoice.data.id)}
      onEditDocuments={() => navigate(`/supplier/invoices/new?replace=${encodeURIComponent(invoice.data.id)}`)}
      isRequestingVerification={requestVerification.isPending}
      onRequestRiskReview={() => requestRiskReview.mutate(invoice.data.id)}
      isRequestingRiskReview={requestRiskReview.isPending}
      riskReviewError={requestRiskReview.error instanceof Error ? requestRiskReview.error.message : undefined}
    />
  );
}
