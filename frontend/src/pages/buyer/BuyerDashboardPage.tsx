import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";

const fallbackRequests = [
  {
    id: "INV-2026-001",
    supplier: "Alpha Components",
    amountKrw: 20_000_000,
    dueDateEnglish: "Oct 30, 2026",
    dueDateKorean: "2026년 10월 30일",
    primary: true,
  },
  {
    id: "INV-2026-018",
    supplier: "Hanul Parts",
    amountKrw: 31_200_000,
    dueDateEnglish: "Nov 05, 2026",
    dueDateKorean: "2026년 11월 5일",
    primary: false,
  },
] as const;

const krw = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "KRW",
  maximumFractionDigits: 0,
});

export function BuyerDashboardPage() {
  const invoices = useInvoices();
  const { t } = useLanguage();

  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;

  const primaryInvoice = invoices.data?.[0];
  const requests = fallbackRequests.map((request, index) => (
    index === 0 && primaryInvoice
      ? {
          ...request,
          id: primaryInvoice.id,
          supplier: primaryInvoice.supplier.name,
          amountKrw: primaryInvoice.invoiceAmountKrw,
        }
      : request
  ));

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
          <strong>3 <small>{t("invoices", "건")}</small></strong>
        </article>
        <article>
          <span>{t("Due in 30 days", "30일 이내 만기")}</span>
          <strong>₩68.4M</strong>
        </article>
        <article>
          <span>{t("Completed this month", "이번 달 완료")}</span>
          <strong>12</strong>
        </article>
      </div>

      <section className="buyer-request-card">
        <header>
          <h2>{t("New verification requests", "새 확인 요청")}</h2>
          <button type="button" className="secondary-button buyer-view-all">
            {t("View all", "전체 보기")}
          </button>
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
              {requests.map((request) => (
                <tr key={request.id}>
                  <td><strong>{request.id}</strong></td>
                  <td>{request.supplier}</td>
                  <td>{krw.format(request.amountKrw)}</td>
                  <td>{t(request.dueDateEnglish, request.dueDateKorean)}</td>
                  <td>
                    <Link
                      className={request.primary ? "buyer-review-link is-primary" : "buyer-review-link"}
                      to={`/buyer/invoices/${request.id}?section=verification`}
                      aria-label={t(`Review ${request.id}`, `${request.id} 확인`)}
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
    </section>
  );
}
