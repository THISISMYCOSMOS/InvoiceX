import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { InvoiceProgress } from "../../components/InvoiceProgress";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { useAcceptOffer } from "../../hooks/useAcceptOffer";
import { useConnectedSolanaWallet } from "../../hooks/useConnectedSolanaWallet";
import { useInvoice } from "../../hooks/useInvoice";
import { useRequestVerification } from "../../hooks/useRequestVerification";
import { isExceptionStatus, type Invoice } from "../../types/invoice";
import { BuyerReviewPendingSection } from "./sections/BuyerReviewPendingSection";
import { DocumentReviewSection } from "./sections/DocumentReviewSection";
import { EarlySettlementOfferSection } from "./sections/EarlySettlementOfferSection";
import { FundingProgressSection } from "./sections/FundingProgressSection";
import { FundingReceiptSection } from "./sections/FundingReceiptSection";
import { InvoiceExceptionSection } from "./sections/InvoiceExceptionSection";
import { SettlementReceiptSection } from "./sections/SettlementReceiptSection";
import { useLanguage } from "../../i18n/LanguageContext";

export function SupplierInvoiceDetailContent({
  invoice,
  onAccept,
  onDecline = () => undefined,
  onRequestVerification = () => undefined,
  isRequestingVerification = false,
  connectedWalletAddress,
  requireConnectedWallet = false,
  isAcceptingOffer = false,
  acceptOfferError,
}: {
  invoice: Invoice;
  onAccept: () => void;
  onDecline?: () => void;
  onRequestVerification?: () => void;
  isRequestingVerification?: boolean;
  connectedWalletAddress?: string | null;
  requireConnectedWallet?: boolean;
  isAcceptingOffer?: boolean;
  acceptOfferError?: unknown;
}) {
  const { t } = useLanguage();
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
        onDecline={onDecline}
        connectedWalletAddress={connectedWalletAddress}
        requireConnectedWallet={requireConnectedWallet}
        isAccepting={isAcceptingOffer}
        error={acceptOfferError}
      />
    );
  }

  if (isExceptionStatus(invoice.status)) {
    return <InvoiceExceptionSection invoice={invoice} />;
  }

  let section = <section><h2>{t("Invoice progress", "인보이스 진행 상태")}</h2></section>;
  if (invoice.status === "FUNDING") section = <FundingProgressSection />;
  if (invoice.status === "FUNDED") section = <FundingReceiptSection invoice={invoice} />;
  if (invoice.status === "SETTLED") section = <SettlementReceiptSection invoice={invoice} />;
  return <><h1>{invoice.id}</h1><StatusBadge status={invoice.status} /><InvoiceProgress status={invoice.status} />{section}</>;
}

export function SupplierInvoiceDetailPage() {
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const invoice = useInvoice(invoiceId);
  const wallet = useConnectedSolanaWallet();
  const acceptOffer = useAcceptOffer();
  const requestVerification = useRequestVerification();
  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) return <ErrorState error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))} />;
  return (
    <SupplierInvoiceDetailContent
      invoice={invoice.data}
      onAccept={() => {
        if (!wallet.publicKey) return;
        acceptOffer.mutate({
          invoiceId: invoice.data.id,
          response: "ACCEPT",
          supplierWalletAddress: wallet.publicKey,
        });
      }}
      onDecline={() => acceptOffer.mutate({ invoiceId: invoice.data.id, response: "DECLINE" })}
      onRequestVerification={() => requestVerification.mutate(invoice.data.id)}
      isRequestingVerification={requestVerification.isPending}
      connectedWalletAddress={wallet.publicKey}
      requireConnectedWallet
      isAcceptingOffer={acceptOffer.isPending}
      acceptOfferError={acceptOffer.error}
    />
  );
}
