import { useMemo, useState } from "react";
import { CurrencyKrw } from "@phosphor-icons/react";
import { useParams, useSearchParams } from "react-router-dom";
import invoicePreview from "../../assets/invoice-preview.png";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useBuyerConfirm } from "../../hooks/useBuyerConfirm";
import { useInvoice } from "../../hooks/useInvoice";
import { useLanguage } from "../../i18n/LanguageContext";
import type { Invoice, InvoiceStatus } from "../../types/invoice";

type BuyerView = "verification" | "payment";
type VerificationChoice = "match" | "mismatch";

const documentTabs = [
  { key: "Invoice", english: "Invoice", korean: "인보이스" },
  { key: "Contract", english: "Contract", korean: "계약서" },
  { key: "PO", english: "PO", korean: "발주서" },
  { key: "Delivery proof", english: "Delivery proof", korean: "납품 증빙" },
] as const;
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

function formatDate(date: string, locale: "en-US" | "ko-KR") {
  return new Intl.DateTimeFormat(locale, {
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
  const { language, t } = useLanguage();
  const [activeTab, setActiveTab] = useState<(typeof documentTabs)[number]["key"]>("Invoice");
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
    { key: "transaction", label: t("Transaction exists", "거래 존재 여부"), positive: t("Match", "일치"), negative: t("Mismatch", "불일치") },
    { key: "supplier", label: t("Supplier information", "공급기업 정보"), positive: t("Match", "일치"), negative: t("Mismatch", "불일치") },
    { key: "amount", label: `${t("Invoice amount", "인보이스 금액")} · ${krw.format(invoice.invoiceAmountKrw)}`, positive: t("Match", "일치"), negative: t("Mismatch", "불일치") },
    { key: "dueDate", label: `${t("Due date", "만기일")} · ${formatDate(invoice.dueDate, language === "ko" ? "ko-KR" : "en-US")}`, positive: t("Match", "일치"), negative: t("Mismatch", "불일치") },
    { key: "delivery", label: t("Delivery completed", "납품 완료"), positive: t("Confirmed", "확인"), negative: t("Unconfirmed", "미확인") },
    { key: "dispute", label: t("Dispute or payment hold", "분쟁 또는 결제 보류"), positive: t("None", "없음"), negative: t("Exists", "있음") },
  ], [invoice.dueDate, invoice.invoiceAmountKrw, language, t]);

  return (
    <section className="buyer-verification">
      <header className="buyer-detail-heading">
        <div>
          <p className="detail-breadcrumb">{t("Verification Requests", "확인 요청")} / {invoice.id}</p>
          <h1>{t(`Verify invoice ${invoice.id}`, `인보이스 ${invoice.id} 확인`)}</h1>
          <p>{t("Compare the supplier submission with your contract, PO, and inspection records.", "공급기업 제출 자료를 계약서, 발주서 및 검수 기록과 비교하세요.")}</p>
        </div>
        <span className="request-date-chip">{t("Requested Jul 29", "7월 29일 요청")}</span>
      </header>

      <div className="buyer-verification-grid">
        <section className="document-compare-card" aria-label={t("Submitted documents", "제출 문서")}>
          <div className="document-tabs" role="tablist" aria-label={t("Submitted document types", "제출 문서 유형")}>
            {documentTabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.key}
                className={activeTab === tab.key ? "is-active" : ""}
                onClick={() => setActiveTab(tab.key)}
              >
                {t(tab.english, tab.korean)}
              </button>
            ))}
          </div>
          <div className="document-preview">
            <img src={invoicePreview} alt={t(`${activeTab} document preview`, `${activeTab} 문서 미리보기`)} />
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
              className="secondary-button"
              onClick={() => setMessage(t("Revision request prepared for the supplier.", "공급기업에 보낼 수정 요청을 준비했습니다."))}
            >
              {t("Request revision", "수정 요청")}
            </button>
            <button
              type="button"
              className="buyer-confirm-button"
              onClick={() => {
                onConfirm();
                setMessage(t("Invoice confirmation submitted.", "인보이스 확인을 제출했습니다."));
              }}
              disabled={!canConfirm}
            >
              {t("Confirm invoice", "인보이스 확인")}
            </button>
          </footer>
          {message && <p className="inline-status" role="status">{message}</p>}
        </section>
      </div>
    </section>
  );
}

function MaturityPaymentSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);
  const accountNumber = "123-456-789012";
  const paymentGuide = [
    `${t("Invoice", "인보이스")}: ${invoice.id}`,
    `${t("Amount", "금액")}: ${krw.format(invoice.invoiceAmountKrw)}`,
    `${t("Bank", "은행")}: OOBank`,
    `${t("Virtual account", "가상계좌")}: ${accountNumber}`,
    `${t("Account holder", "예금주")}: InvoiceX Settlement Partner`,
  ].join("\n");

  const copyAccount = async () => {
    await navigator.clipboard?.writeText(accountNumber);
    setCopied(true);
  };

  return (
    <section className="buyer-payment">
      <header className="buyer-detail-heading">
        <div>
          <p className="detail-breadcrumb">{t("Payment Schedule", "결제 일정")} / {invoice.id}</p>
          <h1>{t("Pay invoice amount", "인보이스 금액 결제")}</h1>
          <p>{t("Transfer the KRW amount to the dedicated virtual account by the contractual due date.", "계약상 만기일까지 원화 금액을 전용 가상계좌로 이체하세요.")}</p>
        </div>
        <span className="payment-pending-chip">{t("KRW PAYMENT PENDING", "원화 결제 대기")}</span>
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
              <dd>{krw.format(invoice.invoiceAmountKrw)}</dd>
            </div>
            <div><dt>{t("Payment deadline", "결제 기한")}</dt><dd>{t("October 30, 2026", "2026년 10월 30일")}</dd></div>
            <div><dt>{t("Bank", "은행")}</dt><dd>OOBank</dd></div>
            <div><dt>{t("Virtual account", "가상계좌")}</dt><dd>{accountNumber}</dd></div>
            <div><dt>{t("Account holder", "예금주")}</dt><dd>InvoiceX Settlement Partner</dd></div>
          </dl>
          <footer>
            <button type="button" className="copy-account-button" onClick={copyAccount}>
              {copied ? t("Account number copied", "계좌번호 복사 완료") : t("Copy account number", "계좌번호 복사")}
            </button>
            <a
              className="secondary-button payment-guide-link"
              href={`data:text/plain;charset=utf-8,${encodeURIComponent(paymentGuide)}`}
              download={`InvoiceX-${invoice.id}-payment-guide.txt`}
            >
              {t("Download payment guide", "결제 안내 다운로드")}
            </a>
          </footer>
        </section>

        <section className="payment-status-card">
          <header><h2>{t("Current status", "현재 상태")}</h2></header>
          <div>
            <span className="krw-status-icon" aria-hidden="true"><CurrencyKrw size={26} /></span>
            <h3>{t("Waiting for KRW payment", "원화 결제 대기 중")}</h3>
            <p>{t("The status updates automatically after the bank confirms receipt. No manual payment confirmation is required.", "은행이 입금을 확인하면 상태가 자동으로 갱신됩니다. 별도의 수동 결제 확인은 필요하지 않습니다.")}</p>
          </div>
        </section>
      </div>
      <p className="payment-processing-note">{t("The amount and virtual account must match for automatic processing.", "자동 처리를 위해 금액과 가상계좌가 정확히 일치해야 합니다.")}</p>
    </section>
  );
}

function BuyerInvoiceIdleSection({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  return (
    <section className="buyer-idle-state">
      <h1>{t(`Invoice ${invoice.id}`, `인보이스 ${invoice.id}`)}</h1>
      <p>{t("There is no buyer action required for this invoice right now.", "현재 이 인보이스에 대해 구매기업이 수행할 작업은 없습니다.")}</p>
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
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const invoice = useInvoice(invoiceId);
  const confirm = useBuyerConfirm();
  const view = searchParams.get("section") === "payment" ? "payment" : "verification";

  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) {
    return <ErrorState error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))} />;
  }

  return (
    <BuyerInvoiceDetailContent
      invoice={invoice.data}
      view={view}
      onConfirm={() => invoice.data.verificationId && confirm.mutate(invoice.data.verificationId)}
    />
  );
}
