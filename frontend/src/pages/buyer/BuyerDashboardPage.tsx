import { Link } from "react-router-dom";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { useInvoices } from "../../hooks/useInvoices";

export function BuyerDashboardPage() {
  const invoices = useInvoices();
  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;
  const items = invoices.data ?? [];
  const review = items.filter((invoice) => invoice.status === "BUYER_REVIEW");
  const payment = items.filter((invoice) => ["FUNDED", "REPAYMENT_PENDING", "SETTLING"].includes(invoice.status));
  const list = (title: string, invoicesToShow: typeof items) => <section><h2>{title}</h2>{invoicesToShow.length === 0 ? <EmptyState message="해당 인보이스가 없습니다." /> : <ul>{invoicesToShow.map((invoice) => <li key={invoice.id}><Link to={`/buyer/invoices/${invoice.id}`}>{invoice.id}</Link> <StatusBadge status={invoice.status} /></li>)}</ul>}</section>;
  return <section><h1>Prime Mobility</h1>{list("확인이 필요한 인보이스", review)}{list("지급 예정 인보이스", payment)}</section>;
}
