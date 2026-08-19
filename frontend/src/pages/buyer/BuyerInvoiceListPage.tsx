import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { getInvoiceDisplayReference, useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatInvoiceAmount } from "../../types/invoice";

type BuyerListKind = "verification" | "payment";

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

  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;

  const locale = language === "ko" ? "ko-KR" : "en-US";
  const isPayment = kind === "payment";
  const allInvoices = invoices.data ?? [];
  const verificationRequests = allInvoices.filter((invoice) => invoice.status === "BUYER_REVIEW");
  const confirmedVerificationInvoices = allInvoices.filter((invoice) => (
    Boolean(invoice.verificationId) && invoice.status !== "BUYER_REVIEW"
  ));
  const items = isPayment
    ? allInvoices.filter((invoice) => (
      invoice.status === "FUNDED" || invoice.status === "REPAYMENT_PENDING" || invoice.status === "SETTLING"
    ))
    : verificationRequests;
  const heading = isPayment
    ? t("Payment schedule", "결제 일정")
    : t("Verification requests", "확인 요청");
  const description = isPayment
    ? t("Review all invoices that require USD payment.", "USD 지급이 필요한 모든 인보이스를 확인하세요.")
    : t("Review pending requests and confirmed supplier invoices.", "구매기업 확인 대기 및 완료 인보이스를 모두 확인하세요.");

  return (
    <section className="buyer-dashboard buyer-invoice-list-page">
      <header className="buyer-page-heading">
        <h1>{heading}</h1>
        <p>{description}</p>
      </header>

      <section className={`buyer-request-card${isPayment ? " buyer-payment-due-card" : ""}`}>
        <header>
          <div>
            <h2>{isPayment ? t("All payment items", "전체 결제 일정") : t("Pending verification requests", "확인 대기 요청")}</h2>
            {isPayment && <p>{t("Invoices approaching their contractual due date", "계약상 만기일이 가까워진 인보이스")}</p>}
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
                {isPayment && <th>{t("Remaining", "남은 기간")}</th>}
                <th>{t("Action", "작업")}</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={isPayment ? 6 : 5} className="buyer-empty-row">
                    {isPayment
                      ? t("No payments are due right now.", "현재 결제가 필요한 인보이스가 없습니다.")
                      : t("No verification requests are waiting.", "대기 중인 확인 요청이 없습니다.")}
                  </td>
                </tr>
              ) : items.map((invoice) => {
                const daysRemaining = Math.max(0, Math.ceil((new Date(`${invoice.dueDate}T00:00:00`).getTime() - new Date().getTime()) / (24 * 60 * 60 * 1_000)));
                const actionLabel = isPayment ? t("Pay now", "결제하기") : t("Review", "확인");
                const actionDescription = isPayment
                  ? t(`Pay ${getInvoiceDisplayReference(invoice)}`, `${getInvoiceDisplayReference(invoice)} 결제하기`)
                  : t(`Review ${getInvoiceDisplayReference(invoice)}`, `${getInvoiceDisplayReference(invoice)} 확인`);
                return (
                  <tr key={invoice.id}>
                    <td><strong>{getInvoiceDisplayReference(invoice)}</strong></td>
                    <td>{invoice.supplier.name}</td>
                    <td>{formatInvoiceAmount(invoice.invoiceAmount, invoice.currency, locale)}</td>
                    <td>{formatDueDate(invoice.dueDate, locale)}</td>
                    {isPayment && <td><span className="due-soon-pill">{t(`${daysRemaining} days left`, `${daysRemaining}일 남음`)}</span></td>}
                    <td>
                      <Link
                        className="buyer-review-link is-primary"
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
