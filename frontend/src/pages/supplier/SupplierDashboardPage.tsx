import { Plus } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoices } from "../../hooks/useInvoices";
import {
  getInvoiceStatusLabel,
  isExceptionStatus,
  type InvoiceStatus,
} from "../../types/invoice";
import { supplierWalletSummary } from "../../utils/supplierWallet";
import { useLanguage } from "../../i18n/LanguageContext";

/** Colour the row by what the status means, not by a fixed demo palette. */
function statusTone(status: InvoiceStatus): string {
  if (status === "SETTLED" || status === "FUNDED") return "green";
  if (isExceptionStatus(status)) return "amber";
  return "blue";
}

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
  const wallet = supplierWalletSummary(items);
  const usdc = new Intl.NumberFormat("en-US");
  const dateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
  const statusLabel = (status: InvoiceStatus) => language === "ko"
    ? getInvoiceStatusLabel(status)
    : status.replaceAll("_", " ").toLowerCase();

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
          <strong>{usdc.format(wallet.totalReceivedUsdc)} <small>USDC</small></strong>
        </section>
        <section className="stat-card">
          <span>{t("In early settlement", "조기정산 진행 중")}</span>
          <strong>{wallet.inProgressCount} <small>{t("invoices", "건")}</small></strong>
        </section>
        <section className="stat-card">
          <span>{t("Waiting for buyer", "구매자 응답 대기")}</span>
          <strong>{wallet.awaitingBuyerCount} <small>{t("requests", "건")}</small></strong>
        </section>
        <section className="stat-card">
          <span>{t("Early settlement received", "조기정산 수령액")}</span>
          <strong>{usdc.format(wallet.receivedUsdc)} <small>USDC</small></strong>
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
                {items.map((invoice) => (
                  <tr key={invoice.id}>
                    <td>
                      <Link
                        to={`/supplier/invoices/${invoice.id}`}
                        aria-label={t(`View invoice ${invoice.id}`, `${invoice.id} 상세 보기`)}
                      >
                        {invoice.id}
                      </Link>
                    </td>
                    <td>{invoice.buyer.name}</td>
                    <td>{krwFormatter.format(invoice.invoiceAmountKrw)}</td>
                    <td>{dateFormatter.format(new Date(`${invoice.dueDate}T00:00:00`))}</td>
                    <td><span className={`dashboard-status dashboard-status--${statusTone(invoice.status)}`}>{statusLabel(invoice.status)}</span></td>
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
