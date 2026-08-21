import { useState } from "react";
import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { getInvoiceDisplayReference, useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatInvoiceAmount } from "../../types/invoice";

type BuyerListKind = "verification" | "payment";
type PaymentListTab = "scheduled" | "completed";

function formatDueDate(dueDate: string, locale: "en-US" | "ko-KR") {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(new Date(`${dueDate}T00:00:00`));
}

function formatConfirmationTime(value: string | undefined, locale: "en-US" | "ko-KR") {
  if (!value) return "—";
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

function BuyerInvoiceListPage({ kind }: { kind: BuyerListKind }) {
  const invoices = useInvoices();
  const { language, t } = useLanguage();
  const [paymentTab, setPaymentTab] = useState<PaymentListTab>("scheduled");

  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;

  const locale = language === "ko" ? "ko-KR" : "en-US";
  const isPayment = kind === "payment";
  const allInvoices = invoices.data ?? [];
  const verificationRequests = allInvoices.filter((invoice) => invoice.status === "BUYER_REVIEW");
  const confirmedVerificationInvoices = allInvoices.filter((invoice) => (
    Boolean(invoice.verificationId) && invoice.status !== "BUYER_REVIEW"
  ));
  const scheduledPayments = allInvoices.filter((invoice) => (
    invoice.status === "FUNDED"
    || invoice.status === "REPAYMENT_PENDING"
    || invoice.status === "SETTLING"
    || invoice.status === "SETTLEMENT_FAILED"
  ));
  const completedPayments = allInvoices.filter((invoice) => invoice.status === "SETTLED");
  const items = isPayment
    ? paymentTab === "scheduled" ? scheduledPayments : completedPayments
    : verificationRequests;
  const showingCompletedPayments = isPayment && paymentTab === "completed";
  const heading = isPayment
    ? t("Payment list", "결제 목록")
    : t("Verification requests", "확인 요청");
  const description = isPayment
    ? t("Review scheduled and completed USDC payments.", "예정 및 완료된 USDC 결제 내역을 확인하세요.")
    : t("Review pending requests and confirmed supplier invoices.", "구매기업 확인 대기 및 완료 인보이스를 모두 확인하세요.");

  return (
    <section className="buyer-dashboard buyer-invoice-list-page">
      <header className="buyer-page-heading">
        <h1>{heading}</h1>
        <p>{description}</p>
      </header>

      {isPayment && (
        <div className="investor-activity-filters investor-policy-tabs buyer-payment-tabs" role="tablist" aria-label={t("Payment list sections", "결제 목록 구분")}>
          <button
            id="scheduled-payments-tab"
            type="button"
            role="tab"
            aria-selected={paymentTab === "scheduled"}
            aria-controls="buyer-payment-list-panel"
            className={paymentTab === "scheduled" ? "is-active" : ""}
            onClick={() => setPaymentTab("scheduled")}
          >
            {t("Payment schedule", "결제 일정")}
          </button>
          <button
            id="completed-payments-tab"
            type="button"
            role="tab"
            aria-selected={paymentTab === "completed"}
            aria-controls="buyer-payment-list-panel"
            className={paymentTab === "completed" ? "is-active" : ""}
            onClick={() => setPaymentTab("completed")}
          >
            {t("Completed payments", "결제 완료 목록")}
          </button>
        </div>
      )}

      <section
        id={isPayment ? "buyer-payment-list-panel" : undefined}
        className={`buyer-request-card${isPayment ? " buyer-payment-due-card" : ""}`}
        role={isPayment ? "tabpanel" : undefined}
        aria-labelledby={isPayment ? (showingCompletedPayments ? "completed-payments-tab" : "scheduled-payments-tab") : undefined}
      >
        <header>
          <div>
            <h2>{isPayment
              ? showingCompletedPayments
                ? t("Completed payment items", "결제 완료 내역")
                : t("All payment items", "전체 결제 일정")
              : t("Pending verification requests", "확인 대기 요청")}</h2>
            {isPayment && <p>{showingCompletedPayments
              ? t("Invoices with confirmed USDC payment and maturity settlement", "USDC 결제와 만기 정산이 완료된 인보이스")
              : t("Invoices approaching their contractual due date", "계약상 만기일이 가까워진 인보이스")}</p>}
          </div>
          <span className="buyer-due-summary">{t(`${items.length} items`, `${items.length}건`)}</span>
        </header>
        <div className="table-scroll">
          <table aria-label={heading}>
            <thead>
              <tr>
                <th>{t("Invoice", "인보이스")}</th>
                <th>{t("Supplier", "공급기업")}</th>
                <th>{t("Amount", "금액")}</th>
                <th>{t("Due date", "만기일")}</th>
                {isPayment && <th>{showingCompletedPayments ? t("Completed at", "결제 완료일") : t("Remaining", "남은 기간")}</th>}
                <th>{t("Action", "작업")}</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={isPayment ? 6 : 5} className="buyer-empty-row">
                    {isPayment
                      ? showingCompletedPayments
                        ? t("No completed payments yet.", "아직 결제 완료 내역이 없습니다.")
                        : t("No payments are due right now.", "현재 결제가 필요한 인보이스가 없습니다.")
                      : t("No verification requests are waiting.", "대기 중인 확인 요청이 없습니다.")}
                  </td>
                </tr>
              ) : items.map((invoice) => {
                const daysRemaining = Math.max(0, Math.ceil((new Date(`${invoice.dueDate}T00:00:00`).getTime() - new Date().getTime()) / (24 * 60 * 60 * 1_000)));
                const actionLabel = isPayment
                  ? showingCompletedPayments ? t("View details", "상세 보기") : t("Pay now", "결제하기")
                  : t("Review", "확인");
                const actionDescription = isPayment
                  ? showingCompletedPayments
                    ? t(`View ${getInvoiceDisplayReference(invoice)}`, `${getInvoiceDisplayReference(invoice)} 상세 보기`)
                    : t(`Pay ${getInvoiceDisplayReference(invoice)}`, `${getInvoiceDisplayReference(invoice)} 결제하기`)
                  : t(`Review ${getInvoiceDisplayReference(invoice)}`, `${getInvoiceDisplayReference(invoice)} 확인`);
                return (
                  <tr key={invoice.id}>
                    <td><strong>{getInvoiceDisplayReference(invoice)}</strong></td>
                    <td>{invoice.supplier.name}</td>
                    <td>{formatInvoiceAmount(invoice.invoiceAmount, invoice.currency, locale)}</td>
                    <td>{formatDueDate(invoice.dueDate, locale)}</td>
                    {isPayment && <td>{showingCompletedPayments
                      ? formatConfirmationTime(invoice.buyerPaidAt ?? invoice.settlementTransaction?.createdAt, locale)
                      : <span className="due-soon-pill">{t(`${daysRemaining} days left`, `${daysRemaining}일 남음`)}</span>}</td>}
                    <td>
                      <Link
                        className={`buyer-review-link${showingCompletedPayments ? "" : " is-primary"}`}
                        to={`/buyer/invoices/${invoice.id}?section=${kind}`}
                        aria-label={actionDescription}
                      >
                        {actionLabel}
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {!isPayment && (
        <section className="buyer-request-card buyer-confirmed-request-card">
          <header>
            <h2>{t("Confirmed invoices", "확인 완료 인보이스")}</h2>
            <span className="buyer-due-summary">{t(`${confirmedVerificationInvoices.length} items`, `${confirmedVerificationInvoices.length}건`)}</span>
          </header>
          <div className="table-scroll">
            <table aria-label={t("Confirmed invoices", "확인 완료 인보이스")}>
              <thead>
                <tr>
                  <th>{t("Invoice", "인보이스")}</th>
                  <th>{t("Supplier", "공급기업")}</th>
                  <th>{t("Amount", "금액")}</th>
                  <th>{t("Confirmed at", "확인 일시")}</th>
                  <th>{t("Action", "작업")}</th>
                </tr>
              </thead>
              <tbody>
                {confirmedVerificationInvoices.length === 0 ? (
                  <tr><td colSpan={5} className="buyer-empty-row">{t("No invoices have been confirmed yet.", "아직 확인 완료된 인보이스가 없습니다.")}</td></tr>
                ) : confirmedVerificationInvoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <td><strong>{getInvoiceDisplayReference(invoice)}</strong></td>
                    <td>{invoice.supplier.name}</td>
                    <td>{formatInvoiceAmount(invoice.invoiceAmount, invoice.currency, locale)}</td>
                    <td>{formatConfirmationTime(invoice.verificationConfirmedAt ?? invoice.riskPassport?.generatedAt, locale)}</td>
                    <td>
                      <Link
                        className="buyer-review-link"
                        to={`/buyer/invoices/${invoice.id}?section=verification`}
                        aria-label={t(`View details for ${getInvoiceDisplayReference(invoice)}`, `${getInvoiceDisplayReference(invoice)} 상세 보기`)}
                      >
                        {t("View details", "상세 보기")}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </section>
  );
}

export function BuyerVerificationListPage() {
  return <BuyerInvoiceListPage kind="verification" />;
}

export function BuyerPaymentListPage() {
  return <BuyerInvoiceListPage kind="payment" />;
}
