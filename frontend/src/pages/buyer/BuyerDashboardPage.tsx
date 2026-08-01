import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";
import type { Invoice } from "../../types/invoice";

const krw = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "KRW",
  maximumFractionDigits: 0,
});

function formatDueDate(dueDate: string, locale: "en-US" | "ko-KR") {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(new Date(`${dueDate}T00:00:00`));
}

function isDueWithin30Days(invoice: Invoice, now: Date) {
  const dueAt = new Date(`${invoice.dueDate}T00:00:00`).getTime();
  const difference = dueAt - now.getTime();
  return difference >= 0 && difference <= 30 * 24 * 60 * 60 * 1_000;
}

export function BuyerDashboardPage() {
  const invoices = useInvoices();
  const { language, t } = useLanguage();

  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;

  const items = invoices.data ?? [];
  const locale = language === "ko" ? "ko-KR" : "en-US";
  const verificationRequests = items.filter((invoice) => invoice.status === "BUYER_REVIEW");
  const paymentInvoices = items.filter((invoice) => (
    invoice.status === "FUNDED" || invoice.status === "REPAYMENT_PENDING" || invoice.status === "SETTLING"
  ));
  const dueSoonTotal = paymentInvoices
    .filter((invoice) => isDueWithin30Days(invoice, new Date()))
    .reduce((total, invoice) => total + invoice.invoiceAmountKrw, 0);
  const completedCount = items.filter((invoice) => invoice.status === "SETTLED").length;

  return (
    <section className="buyer-dashboard">
      <header className="buyer-page-heading">
        <h1>{t("Invoice verification", "인보이스 확인")}</h1>
        <p>
          {t(
            "Review supplier invoices and manage upcoming payments.",
            "공급기업 인보이스를 확인하고 예정된 결제를 관리하세요.",
          )}
        </p>
      </header>

      <div className="buyer-stats" aria-label={t("Buyer invoice summary", "구매기업 인보이스 요약")}>
        <article>
          <span>{t("New requests", "새 확인 요청")}</span>
          <strong>{verificationRequests.length} <small>{t("invoices", "건")}</small></strong>
        </article>
        <article>
          <span>{t("Due in 30 days", "30일 이내 만기")}</span>
          <strong>{krw.format(dueSoonTotal)}</strong>
        </article>
        <article>
          <span>{t("Completed invoices", "완료된 인보이스")}</span>
          <strong>{completedCount}</strong>
        </article>
      </div>

      <section className="buyer-request-card">
        <header>
          <h2>{t("New verification requests", "새 확인 요청")}</h2>
          <span className="buyer-due-summary">{t(`${verificationRequests.length} requests`, `${verificationRequests.length}건 요청`)}</span>
        </header>
        <div className="table-scroll">
          <table aria-label={t("New verification requests", "새 확인 요청")}>
            <thead>
              <tr>
                <th>{t("Invoice", "인보이스")}</th>
                <th>{t("Supplier", "공급기업")}</th>
                <th>{t("Amount", "금액")}</th>
                <th>{t("Due date", "만기일")}</th>
                <th>{t("Action", "작업")}</th>
              </tr>
            </thead>
            <tbody>
              {verificationRequests.length === 0 ? (
                <tr><td colSpan={5} className="buyer-empty-row">{t("No verification requests are waiting.", "대기 중인 확인 요청이 없습니다.")}</td></tr>
              ) : verificationRequests.map((invoice) => (
                <tr key={invoice.id}>
                  <td><strong>{invoice.id}</strong></td>
                  <td>{invoice.supplier.name}</td>
                  <td>{krw.format(invoice.invoiceAmountKrw)}</td>
                  <td>{formatDueDate(invoice.dueDate, locale)}</td>
                  <td>
                    <Link
                      className="buyer-review-link is-primary"
                      to={`/buyer/invoices/${invoice.id}?section=verification`}
                      aria-label={t(`Review ${invoice.id}`, `${invoice.id} 확인`)}
                    >
                      {t("Review", "확인")}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="buyer-request-card buyer-payment-due-card">
        <header>
          <div>
            <h2>{t("Payments due soon", "결제 필요")}</h2>
            <p>{t("Invoices approaching their contractual due date", "계약상 만기일이 가까워진 인보이스")}</p>
          </div>
          <span className="buyer-due-summary">{t(`${paymentInvoices.length} payment items`, `결제 필요 ${paymentInvoices.length}건`)}</span>
        </header>
        <div className="table-scroll">
          <table aria-label={t("Payments due soon", "결제 필요")}>
            <thead>
              <tr>
                <th>{t("Invoice", "인보이스")}</th>
                <th>{t("Supplier", "공급기업")}</th>
                <th>{t("Amount", "금액")}</th>
                <th>{t("Due date", "만기일")}</th>
                <th>{t("Remaining", "남은 기간")}</th>
                <th>{t("Action", "작업")}</th>
              </tr>
            </thead>
            <tbody>
              {paymentInvoices.length === 0 ? (
                <tr><td colSpan={6} className="buyer-empty-row">{t("No payments are due right now.", "현재 결제가 필요한 인보이스가 없습니다.")}</td></tr>
              ) : paymentInvoices.map((invoice) => {
                const daysRemaining = Math.max(0, Math.ceil((new Date(`${invoice.dueDate}T00:00:00`).getTime() - new Date().getTime()) / (24 * 60 * 60 * 1_000)));
                return (
                  <tr key={invoice.id}>
                    <td><strong>{invoice.id}</strong></td>
                    <td>{invoice.supplier.name}</td>
                    <td>{krw.format(invoice.invoiceAmountKrw)}</td>
                    <td>{formatDueDate(invoice.dueDate, locale)}</td>
                    <td><span className="due-soon-pill">{t(`${daysRemaining} days left`, `${daysRemaining}일 남음`)}</span></td>
                    <td>
                      <Link
                        className="buyer-review-link is-primary"
                        to={`/buyer/invoices/${invoice.id}?section=payment`}
                        aria-label={t(`Pay ${invoice.id}`, `${invoice.id} 결제하기`)}
                      >
                        {t("Pay now", "결제하기")}
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
