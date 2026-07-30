import { useMemo, useState } from "react";
import { CurrencyKrw } from "@phosphor-icons/react";
import { useParams, useSearchParams } from "react-router-dom";
import invoicePreview from "../../assets/invoice-preview.png";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useBuyerConfirm } from "../../hooks/useBuyerConfirm";
import { useInvoice } from "../../hooks/useInvoice";
import type { Invoice, InvoiceStatus } from "../../types/invoice";

type BuyerView = "verification" | "payment";
type VerificationChoice = "match" | "mismatch";

const documentTabs = ["Invoice", "Contract", "PO", "Delivery proof"] as const;
const maturityStatuses: InvoiceStatus[] = ["FUNDED", "REPAYMENT_PENDING", "SETTLING"];
const previewableVerificationStatuses: InvoiceStatus[] = [
  "DRAFT",
  "DOCUMENT_UPLOADING",
  "DOCUMENT_ANALYZING",
  "DOCUMENT_REVIEW_REQUIRED",
  "BUYER_REVIEW",
];

const krw = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "KRW",
  maximumFractionDigits: 0,
});

function formatDate(date: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(new Date(`${date}T00:00:00`));
}

function VerificationChoiceButtons({
  value,
  positiveLabel,
  negativeLabel,
  onChange,
}: {
  value: VerificationChoice;
  positiveLabel: string;
  negativeLabel: string;
  onChange: (value: VerificationChoice) => void;
}) {
  return (
    <div className="verification-choice" role="group" aria-label={`${positiveLabel} or ${negativeLabel}`}>
      <button
        type="button"
        className={value === "match" ? "is-selected" : ""}
        aria-pressed={value === "match"}
        onClick={() => onChange("match")}
      >
        {positiveLabel}
      </button>
      <button
        type="button"
        className={value === "mismatch" ? "is-selected is-negative" : ""}
        aria-pressed={value === "mismatch"}
        onClick={() => onChange("mismatch")}
      >
        {negativeLabel}
      </button>
    </div>
  );
}

function BuyerVerificationSection({
  invoice,
  onConfirm,
  canConfirm,
}: {
  invoice: Invoice;
  onConfirm: () => void;
  canConfirm: boolean;
}) {
  const [activeTab, setActiveTab] = useState<(typeof documentTabs)[number]>("Invoice");
  const [message, setMessage] = useState<string>();
  const [choices, setChoices] = useState<Record<string, VerificationChoice>>({
    transaction: "match",
    supplier: "match",
    amount: "match",
    dueDate: "match",
    delivery: "match",
    dispute: "match",
  });

  const rows = useMemo(() => [
    { key: "transaction", label: "Transaction exists", positive: "Match", negative: "Mismatch" },
    { key: "supplier", label: "Supplier information", positive: "Match", negative: "Mismatch" },
    { key: "amount", label: `Invoice amount · ${krw.format(invoice.invoiceAmountKrw)}`, positive: "Match", negative: "Mismatch" },
    { key: "dueDate", label: `Due date · ${formatDate(invoice.dueDate)}`, positive: "Match", negative: "Mismatch" },
    { key: "delivery", label: "Delivery completed", positive: "Confirmed", negative: "Unconfirmed" },
    { key: "dispute", label: "Dispute or payment hold", positive: "None", negative: "Exists" },
  ], [invoice.dueDate, invoice.invoiceAmountKrw]);

  return (
    <section className="buyer-verification">
      <header className="buyer-detail-heading">
        <div>
          <p className="detail-breadcrumb">Verification Requests / {invoice.id}</p>
          <h1>Verify invoice {invoice.id}</h1>
          <p>Compare the supplier submission with your contract, PO, and inspection records.</p>
        </div>
        <span className="request-date-chip">Requested Jul 29</span>
      </header>

      <div className="buyer-verification-grid">
        <section className="document-compare-card" aria-label="Submitted documents">
          <div className="document-tabs" role="tablist" aria-label="Submitted document types">
            {documentTabs.map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={activeTab === tab}
                className={activeTab === tab ? "is-active" : ""}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="document-preview">
            <img src={invoicePreview} alt={`${activeTab} document preview`} />
          </div>
        </section>

        <section className="verification-panel" aria-label="Invoice verification checklist">
          <div className="verification-rows">
            {rows.map((row) => (
              <div className="verification-row" key={row.key}>
                <span>{row.label}</span>
                <VerificationChoiceButtons
                  value={choices[row.key]}
                  positiveLabel={row.positive}
                  negativeLabel={row.negative}
                  onChange={(value) => setChoices((current) => ({ ...current, [row.key]: value }))}
                />
              </div>
            ))}
          </div>
          <p className="verification-note">
            Confirmation verifies the registered transaction and payment schedule. It does not guarantee the buyer&apos;s future ability to pay.
          </p>
          <footer className="verification-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => setMessage("Revision request prepared for the supplier.")}
            >
              Request revision
            </button>
            <button
              type="button"
              className="buyer-confirm-button"
              onClick={() => {
                onConfirm();
                setMessage("Invoice confirmation submitted.");
              }}
              disabled={!canConfirm}
            >
              Confirm invoice
            </button>
          </footer>
          {message && <p className="inline-status" role="status">{message}</p>}
        </section>
      </div>
    </section>
  );
}

function MaturityPaymentSection({ invoice }: { invoice: Invoice }) {
  const [copied, setCopied] = useState(false);
  const accountNumber = "123-456-789012";
  const paymentGuide = [
    `Invoice: ${invoice.id}`,
    `Amount: ${krw.format(invoice.invoiceAmountKrw)}`,
    "Bank: OOBank",
    `Virtual account: ${accountNumber}`,
    "Account holder: InvoiceX Settlement Partner",
  ].join("\n");

  const copyAccount = async () => {
    await navigator.clipboard?.writeText(accountNumber);
    setCopied(true);
  };

  return (
    <section className="buyer-payment">
      <header className="buyer-detail-heading">
        <div>
          <p className="detail-breadcrumb">Payment Schedule / {invoice.id}</p>
          <h1>Pay invoice amount</h1>
          <p>Transfer the KRW amount to the dedicated virtual account by the contractual due date.</p>
        </div>
        <span className="payment-pending-chip">KRW PAYMENT PENDING</span>
      </header>

      <div className="buyer-payment-grid">
        <section className="payment-information-card">
          <header>
            <h2>Payment information</h2>
            <span>{invoice.id}</span>
          </header>
          <dl>
            <div className="payment-amount-row">
              <dt>Amount to pay</dt>
              <dd>{krw.format(invoice.invoiceAmountKrw)}</dd>
            </div>
            <div><dt>Payment deadline</dt><dd>October 30, 2026</dd></div>
            <div><dt>Bank</dt><dd>OOBank</dd></div>
            <div><dt>Virtual account</dt><dd>{accountNumber}</dd></div>
            <div><dt>Account holder</dt><dd>InvoiceX Settlement Partner</dd></div>
          </dl>
          <footer>
            <button type="button" className="copy-account-button" onClick={copyAccount}>
              {copied ? "Account number copied" : "Copy account number"}
            </button>
            <a
              className="secondary-button payment-guide-link"
              href={`data:text/plain;charset=utf-8,${encodeURIComponent(paymentGuide)}`}
              download={`InvoiceX-${invoice.id}-payment-guide.txt`}
            >
              Download payment guide
            </a>
          </footer>
        </section>

        <section className="payment-status-card">
          <header><h2>Current status</h2></header>
          <div>
            <span className="krw-status-icon" aria-hidden="true"><CurrencyKrw size={26} /></span>
            <h3>Waiting for KRW payment</h3>
            <p>The status updates automatically after the bank confirms receipt. No manual payment confirmation is required.</p>
          </div>
        </section>
      </div>
      <p className="payment-processing-note">The amount and virtual account must match for automatic processing.</p>
    </section>
  );
}

function BuyerInvoiceIdleSection({ invoice }: { invoice: Invoice }) {
  return (
    <section className="buyer-idle-state">
      <h1>Invoice {invoice.id}</h1>
      <p>There is no buyer action required for this invoice right now.</p>
    </section>
  );
}

export function BuyerInvoiceDetailContent({
  invoice,
  onConfirm,
  view,
}: {
  invoice: Invoice;
  onConfirm: () => void;
  view?: BuyerView;
}) {
  const showPayment = view === "payment" || maturityStatuses.includes(invoice.status);
  const showVerification = invoice.status === "BUYER_REVIEW"
    || (view === "verification" && previewableVerificationStatuses.includes(invoice.status));

  if (showPayment) return <MaturityPaymentSection invoice={invoice} />;
  if (showVerification) {
    return (
      <BuyerVerificationSection
        invoice={invoice}
        onConfirm={onConfirm}
        canConfirm={Boolean(invoice.verificationId) || view === "verification"}
      />
    );
  }
  return <BuyerInvoiceIdleSection invoice={invoice} />;
}

export function BuyerInvoiceDetailPage() {
  const { invoiceId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const invoice = useInvoice(invoiceId);
  const confirm = useBuyerConfirm();
  const view = searchParams.get("section") === "payment" ? "payment" : "verification";

  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) {
    return <ErrorState error={invoice.error ?? new Error("Invoice not found.")} />;
  }

  return (
    <BuyerInvoiceDetailContent
      invoice={invoice.data}
      view={view}
      onConfirm={() => invoice.data.verificationId && confirm.mutate(invoice.data.verificationId)}
    />
  );
}
