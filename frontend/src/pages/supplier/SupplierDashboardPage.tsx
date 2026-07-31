import { Plus } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";

const demoRecentInvoices = [
  { id: "INV-2026-001", buyer: "Prime Mobility", amount: 20_000_000, dueDate: "2026-10-30", status: "Buyer review", tone: "blue" },
  { id: "INV-2026-009", buyer: "Global Retail", amount: 12_400_000, dueDate: "2026-09-15", status: "Matching", tone: "amber" },
  { id: "INV-2026-006", buyer: "Neo Logistics", amount: 8_950_000, dueDate: "2026-08-28", status: "Funded", tone: "green" },
  { id: "INV-2026-002", buyer: "Prime Mobility", amount: 17_600_000, dueDate: "2026-08-02", status: "Settled", tone: "slate" },
] as const;

const krwFormatter = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "KRW",
  maximumFractionDigits: 0,
});

export function SupplierDashboardPage() {
  const invoices = useInvoices();
  const { language, t } = useLanguage();
  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;
  const items = invoices.data ?? [];
  const isDemoDashboard = items.length === 1 && items[0]?.id === "INV-2026-001";
  const dateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
  const statusLabel = (status: string) => {
    if (language === "en") return status;
    return ({
      "Buyer review": "구매자 검토",
      Matching: "매칭 중",
      Funded: "정산 완료",
      Settled: "상환 완료",
    } as Record<string, string>)[status] ?? status;
  };

  return (
    <section className="supplier-dashboard">
      <header className="page-heading">
        <div>
          <h1>{t("Good morning, Minjun", "좋은 아침이에요, 민준님")}</h1>
          <p>{t("Track invoices and access working capital faster.", "인보이스를 관리하고 운전자금을 더 빠르게 확보하세요.")}</p>
        </div>
        <Link className="primary-button compact-button" to="/supplier/invoices/new">
          <Plus aria-hidden="true" size={14} weight="bold" />
          {t("New invoice", "새 인보이스")}
        </Link>
      </header>

      <div className="dashboard-stats">
        <section className="stat-card">
          <span>{t("USDC wallet balance", "USDC 지갑 잔액")}</span>
          <strong>24,680 <small>USDC</small></strong>
        </section>
        <section className="stat-card">
          <span>{t("In early settlement", "조기정산 진행 중")}</span>
          <strong>3 <small>{t("invoices", "건")}</small></strong>
        </section>
        <section className="stat-card">
          <span>{t("Waiting for buyer", "구매자 응답 대기")}</span>
          <strong>2 <small>{t("requests", "건")}</small></strong>
        </section>
        <section className="stat-card">
          <span>{t("Settlement received", "수령한 정산금")}</span>
          <strong>42,400 <small>USDC</small></strong>
        </section>
      </div>

      <section className="recent-invoices">
        <header>
          <h2>{t("Recent invoices", "최근 인보이스")}</h2>
          <Link className="secondary-button" to="/supplier/invoices/new">{t("View all", "전체 보기")}</Link>
        </header>
        {items.length === 0 ? (
          <EmptyState message={t("No invoices have been registered.", "등록된 인보이스가 없습니다.")} />
        ) : (
          <div className="table-scroll">
            <table aria-label={t("Recent invoices", "최근 인보이스")}>
              <thead>
                <tr>
                  <th>{t("Invoice", "인보이스")}</th>
                  <th>{t("Buyer", "구매자")}</th>
                  <th>{t("Amount", "금액")}</th>
                  <th>{t("Due date", "만기일")}</th>
                  <th>{t("Status", "상태")}</th>
                </tr>
              </thead>
              <tbody>
                {(isDemoDashboard
                  ? demoRecentInvoices
                  : items.map((invoice) => ({
                      id: invoice.id,
                      buyer: invoice.buyer.name,
                      amount: invoice.invoiceAmountKrw,
                      dueDate: invoice.dueDate,
                      status: invoice.status.replaceAll("_", " ").toLowerCase(),
                      tone: "blue",
                    }))
                ).map((invoice, index) => (
                  <tr key={invoice.id}>
                    <td>
                      {index === 0 && items.some((item) => item.id === invoice.id)
                        ? <Link to={`/supplier/invoices/${invoice.id}`}>{invoice.id}</Link>
                        : <strong>{invoice.id}</strong>}
                    </td>
                    <td>{invoice.buyer}</td>
                    <td>{krwFormatter.format(invoice.amount)}</td>
                    <td>{dateFormatter.format(new Date(`${invoice.dueDate}T00:00:00`))}</td>
                    <td><span className={`dashboard-status dashboard-status--${invoice.tone}`}>{statusLabel(invoice.status)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
