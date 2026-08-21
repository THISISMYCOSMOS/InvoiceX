import { useMemo, useState } from "react";
import { ArrowLeft, CheckCircle, CurrencyDollar } from "@phosphor-icons/react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import invoicePreview from "../../assets/invoice-preview.png";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useBuyerConfirm } from "../../hooks/useBuyerConfirm";
import { useBuyerPayment, useBuyerPaymentPreparation } from "../../hooks/useBuyerPayment";
import { useBuyerReject } from "../../hooks/useBuyerReject";
import { useInvoice } from "../../hooks/useInvoice";
import { getInvoiceDisplayReference } from "../../hooks/useInvoices";
import { useCurrentPrivyAccount } from "../../auth/currentAccount";
import { useSignupAuth } from "../../auth/SignupAuthContext";
import { useLanguage } from "../../i18n/LanguageContext";
import type { DocumentType } from "../../types/documents";
import {
  formatInvoiceAmount,
  type BuyerRejectionReason,
  type BuyerPaymentPreparation,
  type Invoice,
  type InvoiceStatus,
} from "../../types/invoice";

type BuyerView = "verification" | "payment";
type VerificationChoice = "match" | "mismatch";

const documentTabs = [
  { type: "INVOICE", english: "Invoice", korean: "인보이스" },
  { type: "CONTRACT", english: "Contract", korean: "계약서" },
  { type: "PURCHASE_ORDER", english: "PO", korean: "발주서" },
  { type: "DELIVERY_PROOF", english: "Delivery proof", korean: "납품 증빙" },
] as const;
const maturityStatuses: InvoiceStatus[] = ["FUNDED", "REPAYMENT_PENDING", "SETTLING"];
const previewableVerificationStatuses: InvoiceStatus[] = [
  "DRAFT",
  "DOCUMENT_UPLOADING",
  "DOCUMENT_ANALYZING",
  "DOCUMENT_REVIEW_REQUIRED",
  "BUYER_REVIEW",
];
const rejectionReasons: Array<{ value: BuyerRejectionReason; english: string; korean: string }> = [
  { value: "DUPLICATE_INVOICE", english: "Duplicate invoice", korean: "중복 인보이스" },
  { value: "DOCUMENT_MISMATCH", english: "Invoice / contract / PO mismatch", korean: "인보이스 / 계약서 / PO 불일치" },
  { value: "DELIVERY_INCOMPLETE", english: "Delivery or service incomplete", korean: "납품 또는 용역 미완료" },
  { value: "AMOUNT_ERROR", english: "Incorrect amount", korean: "금액 오류" },
  { value: "DUE_DATE_ERROR", english: "Incorrect due date", korean: "만기일 오류" },
  { value: "SUSPECTED_ASSIGNMENT", english: "Suspected prior assignment", korean: "기존 채권 양도 의심" },
  { value: "OTHER", english: "Other", korean: "기타" },
];

function formatDate(date: string, locale: "en-US" | "ko-KR") {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(new Date(`${date}T00:00:00`));
}

function formatRequestTime(value: string, locale: "en-US" | "ko-KR") {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
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
  onReject = () => undefined,
  canConfirm,
  isConfirming,
  isRejecting,
  backPath,
}: {
  invoice: Invoice;
  onConfirm: () => Promise<void> | void;
  onReject?: (reasonCode: BuyerRejectionReason, detail?: string) => Promise<void> | void;
  canConfirm: boolean;
  isConfirming: boolean;
  isRejecting: boolean;
  backPath: string;
}) {
  const { language, t } = useLanguage();
  const [activeTab, setActiveTab] = useState<DocumentType>("INVOICE");
  const [message, setMessage] = useState<string>();
  const [showRejection, setShowRejection] = useState(false);
  const [rejectionReason, setRejectionReason] = useState<BuyerRejectionReason>("DOCUMENT_MISMATCH");
  const [rejectionDetail, setRejectionDetail] = useState("");
  const [choices, setChoices] = useState<Record<string, VerificationChoice>>({
    transaction: "match",
    supplier: "match",
    amount: "match",
    dueDate: "match",
    delivery: "match",
    dispute: "match",
  });

  const rows = useMemo(() => [
    { key: "transaction", label: t("Transaction exists", "거래 존재 여부"), positive: t("Match", "일치"), negative: t("Mismatch", "불일치") },
    { key: "supplier", label: t("Supplier information", "공급기업 정보"), positive: t("Match", "일치"), negative: t("Mismatch", "불일치") },
    { key: "amount", label: `${t("Invoice amount", "인보이스 금액")} · ${formatInvoiceAmount(invoice.invoiceAmount, invoice.currency, language === "ko" ? "ko-KR" : "en-US")}`, positive: t("Match", "일치"), negative: t("Mismatch", "불일치") },
    { key: "dueDate", label: `${t("Due date", "만기일")} · ${formatDate(invoice.dueDate, language === "ko" ? "ko-KR" : "en-US")}`, positive: t("Match", "일치"), negative: t("Mismatch", "불일치") },
    { key: "delivery", label: t("Delivery completed", "납품 완료"), positive: t("Confirmed", "확인"), negative: t("Unconfirmed", "미확인") },
    { key: "dispute", label: t("Dispute or payment hold", "분쟁 또는 결제 보류"), positive: t("None", "없음"), negative: t("Exists", "있음") },
  ], [invoice.currency, invoice.dueDate, invoice.invoiceAmount, language, t]);
  const activeDocument = invoice.documents.find((document) => document.type === activeTab);
  const locale = language === "ko" ? "ko-KR" : "en-US";
  const requestedAt = invoice.verificationRequestedAt;

  const submitConfirmation = async () => {
    setMessage(undefined);
    try {
      await onConfirm();
      setMessage(t("Invoice confirmation submitted.", "인보이스 확인이 제출되었습니다."));
    } catch {
      setMessage(t("We could not submit the invoice confirmation. Please try again.", "인보이스 확인을 제출하지 못했습니다. 다시 시도해 주세요."));
    }
  };

  const submitRejection = async () => {
    setMessage(undefined);
    try {
      await onReject(rejectionReason, rejectionDetail.trim() || undefined);
      setMessage(t("Invoice rejection submitted.", "인보이스 거절 사유가 제출되었습니다."));
    } catch {
      setMessage(t("We could not submit the rejection. Please try again.", "인보이스 거절을 제출하지 못했습니다. 다시 시도해 주세요."));
    }
  };

  return (
    <section className="buyer-verification">
      <Link className="buyer-back-link" to={backPath}>
        <ArrowLeft size={13} weight="bold" aria-hidden="true" />
        {t("Back", "뒤로 가기")}
      </Link>
      <header className="buyer-detail-heading">
        <div>
          <p className="detail-breadcrumb">{t("Verification Requests", "확인 요청")} / {invoice.id}</p>
          <h1>{t(`Verify invoice ${invoice.id}`, `인보이스 ${invoice.id} 확인`)}</h1>
          <p>{t("Compare the supplier submission with your contract, PO, and inspection records.", "공급기업 제출 자료를 계약서, 발주서 및 검수 기록과 비교하세요.")}</p>
        </div>
        <span className="request-date-chip">
          {requestedAt
            ? t(
              `Requested ${formatRequestTime(requestedAt, locale)}`,
              `${formatRequestTime(requestedAt, locale)} 요청`,
            )
            : t("Verification requested", "검증 요청됨")}
        </span>
      </header>

      <div className="buyer-verification-grid">
        <section className="document-compare-card" aria-label={t("Submitted documents", "제출 문서")}>
          <div className="document-tabs" role="tablist" aria-label={t("Submitted document types", "제출 문서 유형")}>
            {documentTabs.map((tab) => (
              <button
                key={tab.type}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.type}
                className={activeTab === tab.type ? "is-active" : ""}
                onClick={() => setActiveTab(tab.type)}
              >
                {t(tab.english, tab.korean)}
              </button>
            ))}
          </div>
          <div className="document-preview">
            {activeDocument?.storageUrl ? (
              <iframe title={activeDocument.fileName} src={activeDocument.storageUrl} />
            ) : (
              <img src={invoicePreview} alt={t(`${activeTab} document preview`, `${activeTab} 문서 미리보기`)} />
            )}
          </div>
        </section>

        <section className="verification-panel" aria-label={t("Invoice verification checklist", "인보이스 확인 체크리스트")}>
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
            {t("Confirmation verifies the registered transaction and payment schedule. It does not guarantee the buyer's future ability to pay.", "확인은 등록된 거래와 결제 일정을 검증하지만 구매기업의 향후 지급 능력을 보장하지 않습니다.")}
          </p>
          <footer className="verification-actions">
            <button
              type="button"
              className="buyer-reject-button"
              onClick={() => setShowRejection((current) => !current)}
              disabled={!canConfirm || isRejecting}
            >
              {t("Reject invoice", "인보이스 거절")}
            </button>
            <button
              type="button"
              className="buyer-confirm-button"
              onClick={() => void submitConfirmation()}
              disabled={!canConfirm || isConfirming}
            >
              {isConfirming ? t("Confirming invoice...", "인보이스 확인 중...") : t("Confirm invoice", "인보이스 확인")}
            </button>
          </footer>
          {showRejection && (
            <div className="buyer-rejection-form">
              <label>
                <span>{t("Rejection reason", "거절 사유")}</span>
                <select value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value as BuyerRejectionReason)}>
                  {rejectionReasons.map((reason) => (
                    <option key={reason.value} value={reason.value}>{t(reason.english, reason.korean)}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>{t("Additional details", "상세 사유")}</span>
                <textarea
                  value={rejectionDetail}
                  onChange={(event) => setRejectionDetail(event.target.value)}
                  placeholder={t("Add evidence or corrections the supplier should review.", "공급기업이 확인할 근거나 수정 내용을 입력하세요.")}
                />
              </label>
              <button type="button" className="buyer-reject-submit" onClick={() => void submitRejection()} disabled={isRejecting}>
                {isRejecting ? t("Submitting...", "제출 중...") : t("Submit rejection", "거절 제출")}
              </button>
            </div>
          )}
          {message && <p className="inline-status" role="status">{message}</p>}
        </section>
      </div>
    </section>
  );
}

function MaturityPaymentSection({
  invoice,
  preparation,
  onPay,
  isPaying = false,
  walletSignIn,
  isWalletLoading = false,
  paymentError,
  paymentComplete = false,
}: {
  invoice: Invoice;
  preparation?: BuyerPaymentPreparation;
  onPay?: () => void;
  isPaying?: boolean;
  walletSignIn?: { email: string; returnTo: string };
  isWalletLoading?: boolean;
  paymentError?: string;
  paymentComplete?: boolean;
}) {
  const { language, t } = useLanguage();
  const accountNumber = preparation?.settlementWalletAddress ?? "—";

  return (
    <section className="buyer-payment">
      <header className="buyer-detail-heading">
        <div>
          <p className="detail-breadcrumb">{t("Payment Schedule", "결제 일정")} / {invoice.id}</p>
          <h1>{t("Pay invoice amount", "인보이스 금액 결제")}</h1>
          <p>{t("Transfer the USDC amount to the designated settlement address by the contractual due date.", "계약상 만기일까지 USDC 금액을 지정 정산 주소로 이체하세요.")}</p>
        </div>
        <span className="payment-pending-chip">{t("USDC PAYMENT PENDING", "USDC 결제 대기")}</span>
      </header>

      <div className="buyer-payment-grid">
        <section className="payment-information-card">
          <header>
            <h2>{t("Payment information", "결제 정보")}</h2>
            <span>{invoice.id}</span>
          </header>
          <dl>
            <div className="payment-amount-row">
              <dt>{t("Amount to pay", "결제 금액")}</dt>
              <dd>{formatInvoiceAmount(preparation?.amountUsdc ?? invoice.invoiceAmount, "USDC")}</dd>
            </div>
            <div><dt>{t("Payment deadline", "결제 기한")}</dt><dd>{formatDate(preparation?.dueDate ?? invoice.dueDate, language === "ko" ? "ko-KR" : "en-US")}</dd></div>
            <div><dt>{t("Network", "네트워크")}</dt><dd>Solana Devnet</dd></div>
            <div><dt>{t("Settlement address", "정산 주소")}</dt><dd className="settlement-wallet-address">{accountNumber}</dd></div>
            <div><dt>{t("Asset", "결제 자산")}</dt><dd>Devnet USDC</dd></div>
          </dl>
          <footer>
            {walletSignIn ? (
              <Link
                className="buyer-confirm-button buyer-confirm-button--full buyer-wallet-sign-in-link"
                state={{ authOnly: true, email: walletSignIn.email, returnTo: walletSignIn.returnTo }}
                to="/signup"
              >
                {t("Sign in to wallet and pay", "지갑 로그인 후 결제")}
              </Link>
            ) : (
              <button type="button" className="buyer-confirm-button buyer-confirm-button--full" onClick={onPay} disabled={!preparation || !onPay || isPaying || isWalletLoading}>
                {isWalletLoading
                  ? t("Checking embedded wallet...", "임베디드 지갑 확인 중...")
                  : isPaying
                    ? t("Confirming payment...", "결제 확인 중...")
                    : t("Pay with embedded wallet", "임베디드 지갑으로 결제")}
              </button>
            )}
          </footer>
        </section>

        <section className="payment-status-card">
          <header><h2>{t("Current status", "현재 상태")}</h2></header>
          <div>
            <span className="krw-status-icon" aria-hidden="true"><CurrencyDollar size={26} /></span>
            <h3>{t("Waiting for USDC payment", "USDC 결제 대기 중")}</h3>
            <p>{t("The status updates automatically after the transfer is confirmed. No manual payment confirmation is required.", "전송이 확인되면 상태가 자동으로 갱신됩니다. 별도의 수동 결제 확인은 필요하지 않습니다.")}</p>
          </div>
        </section>
      </div>
      {paymentError && <p className="wallet-error" role="alert">{paymentError}</p>}
      {paymentComplete && <p className="inline-status" role="status">{t("USDC payment and settlement were confirmed.", "USDC 결제와 정산이 확인되었습니다.")}</p>}
    </section>
  );
}

function BuyerInvoiceIdleSection({ invoice }: { invoice: Invoice }) {
  const { language, t } = useLanguage();
  const locale = language === "ko" ? "ko-KR" : "en-US";
  const originalInvoiceNumber = getInvoiceDisplayReference(invoice);
  const deliveryCompleted = invoice.analysis?.deliveryCompleted.value;
  const confirmationTimestamp = invoice.verificationConfirmedAt ?? invoice.riskPassport?.generatedAt;
  const confirmationTime = confirmationTimestamp
    ? new Intl.DateTimeFormat(locale, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(confirmationTimestamp))
    : "—";

  return (
    <section className="buyer-idle-state">
      <Link className="buyer-back-link" to="/buyer/verification">
        <ArrowLeft size={13} weight="bold" aria-hidden="true" />
        {t("Back to verification requests", "확인 요청 목록으로")}
      </Link>
      <div className="signup-progress buyer-confirmation-progress" aria-label={t("Verification progress", "인보이스 확인 진행 상황")}>
        <div>
          <strong>{t("2 / 2 Buyer confirmation complete", "2 / 2 구매기업 확인 완료")}</strong>
          <span>{t("Invoice verification", "인보이스 확인")}</span>
        </div>
        <i><b className="signup-progress__fill signup-progress__fill--complete" /></i>
      </div>

      <header className="buyer-confirmed-heading">
        <span className="buyer-confirmed-heading__icon" aria-hidden="true"><CheckCircle size={24} weight="fill" /></span>
        <div>
          <span>{t("BUYER CONFIRMATION COMPLETE", "구매기업 확인 완료")}</span>
          <h1>{t("Invoice verification completed", "인보이스 확인이 완료되었습니다")}</h1>
          <p>{t("Your confirmation has been recorded for this invoice.", "인보이스 확인 기록이 등록되었습니다.")}</p>
        </div>
        <span className="buyer-complete-card__status">{t("CONFIRMED", "확인 완료")}</span>
      </header>

      <div className="buyer-confirmed-details">
        <section>
          <h2>{t("Transaction information", "거래 정보")}</h2>
          <dl>
            <div><dt>{t("Original invoice number", "원본 인보이스 번호")}</dt><dd>{originalInvoiceNumber}</dd></div>
            <div><dt>{t("Supplier", "공급기업")}</dt><dd>{invoice.supplier.name}</dd></div>
            <div><dt>{t("Invoice amount", "인보이스 금액")}</dt><dd>{formatInvoiceAmount(invoice.invoiceAmount, invoice.currency, locale)}</dd></div>
            <div><dt>{t("Due date", "만기일")}</dt><dd>{formatDate(invoice.dueDate, locale)}</dd></div>
          </dl>
        </section>
        <section>
          <h2>{t("Transaction evidence", "거래 근거")}</h2>
          <dl>
            <div><dt>{t("Contract number", "계약번호")}</dt><dd>{invoice.contractNumber || "—"}</dd></div>
            <div><dt>{t("PO number", "PO 번호")}</dt><dd>{invoice.purchaseOrderNumber || "—"}</dd></div>
            <div><dt>{t("Delivery status", "납품 상태")}</dt><dd>{deliveryCompleted === true ? t("Complete", "완료") : deliveryCompleted === false ? t("Not completed", "미완료") : t("Needs confirmation", "확인 필요")}</dd></div>
            <div><dt>{t("Dispute status", "분쟁 상태")}</dt><dd>{t("None", "없음")}</dd></div>
          </dl>
        </section>
        <section>
          <h2>{t("Confirmation record", "확인 기록")}</h2>
          <dl>
            <div><dt>{t("Confirming company", "확인 기업")}</dt><dd>{invoice.buyer.name}</dd></div>
            <div><dt>{t("Confirmed at", "확인 일시")}</dt><dd>{confirmationTime}</dd></div>
            <div><dt>{t("Confirmation status", "확인 상태")}</dt><dd className="buyer-confirmed-status"><CheckCircle size={13} weight="fill" aria-hidden="true" /> Buyer Confirmed</dd></div>
          </dl>
        </section>
      </div>
    </section>
  );
}

export function BuyerInvoiceDetailContent({
  invoice,
  onConfirm,
  onReject = () => undefined,
  view,
  isConfirming = false,
  isRejecting = false,
  paymentPreparation,
  onPay,
  isPaying = false,
  walletSignIn,
  isWalletLoading = false,
  paymentError,
  paymentComplete = false,
}: {
  invoice: Invoice;
  onConfirm: () => Promise<void> | void;
  onReject?: (reasonCode: BuyerRejectionReason, detail?: string) => Promise<void> | void;
  view?: BuyerView;
  isConfirming?: boolean;
  isRejecting?: boolean;
  paymentPreparation?: BuyerPaymentPreparation;
  onPay?: () => void;
  isPaying?: boolean;
  walletSignIn?: { email: string; returnTo: string };
  isWalletLoading?: boolean;
  paymentError?: string;
  paymentComplete?: boolean;
}) {
  const showPayment = view === "payment" || maturityStatuses.includes(invoice.status);
  const showVerification = invoice.status === "BUYER_REVIEW"
    || (view === "verification" && previewableVerificationStatuses.includes(invoice.status));

  if (showPayment) return (
    <MaturityPaymentSection
      invoice={invoice}
      preparation={paymentPreparation}
      onPay={onPay}
      isPaying={isPaying}
      walletSignIn={walletSignIn}
      isWalletLoading={isWalletLoading}
      paymentError={paymentError}
      paymentComplete={paymentComplete}
    />
  );
  if (showVerification) {
    return (
      <BuyerVerificationSection
        invoice={invoice}
        onConfirm={onConfirm}
        onReject={onReject}
        canConfirm={Boolean(invoice.verificationId)}
        isConfirming={isConfirming}
        isRejecting={isRejecting}
        backPath="/buyer/verification"
      />
    );
  }
  return <BuyerInvoiceIdleSection invoice={invoice} />;
}

export function BuyerInvoiceDetailPage() {
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const currentAccount = useCurrentPrivyAccount();
  const {
    authenticated,
    embeddedSolanaWalletReady,
    hasEmbeddedSolanaWallet,
  } = useSignupAuth();
  const invoice = useInvoice(invoiceId);
  const confirm = useBuyerConfirm();
  const reject = useBuyerReject();
  const paymentPreparation = useBuyerPaymentPreparation(invoiceId);
  const payment = useBuyerPayment(invoiceId);
  const view = searchParams.get("section") === "payment" ? "payment" : "verification";
  const embeddedWalletAddress = currentAccount?.walletAddress;
  const canSignWithEmbeddedWallet = Boolean(
    authenticated
      && embeddedSolanaWalletReady
      && embeddedWalletAddress
      && hasEmbeddedSolanaWallet(embeddedWalletAddress),
  );
  const isWalletLoading = authenticated && !embeddedSolanaWalletReady;
  const walletSignIn = !isWalletLoading && !canSignWithEmbeddedWallet
    ? {
        email: currentAccount?.userEmail ?? "",
        returnTo: `/buyer/invoices/${encodeURIComponent(invoiceId)}?section=payment`,
      }
    : undefined;

  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) {
    return <ErrorState error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))} />;
  }

  return (
    <BuyerInvoiceDetailContent
      invoice={invoice.data}
      view={view}
      onConfirm={() => {
        if (!invoice.data.verificationId) {
          return Promise.reject(new Error("Verification request is unavailable."));
        }
        return confirm.mutateAsync(invoice.data.verificationId).then(() => undefined);
      }}
      onReject={(reasonCode, detail) => {
        if (!invoice.data.verificationId) {
          return Promise.reject(new Error("Verification request is unavailable."));
        }
        return reject.mutateAsync({ verificationId: invoice.data.verificationId, reasonCode, detail }).then(() => undefined);
      }}
      isConfirming={confirm.isPending}
      isRejecting={reject.isPending}
      paymentPreparation={paymentPreparation.data}
      onPay={() => payment.mutate()}
      isPaying={payment.isPending}
      walletSignIn={walletSignIn}
      isWalletLoading={isWalletLoading}
      paymentError={(paymentPreparation.error ?? payment.error)?.message}
      paymentComplete={payment.isSuccess}
    />
  );
}
