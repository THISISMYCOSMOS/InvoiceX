import { Link } from "react-router-dom";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { useInvoices } from "../../hooks/useInvoices";

export function SupplierDashboardPage() {
  const invoices = useInvoices();
  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;
  const items = invoices.data ?? [];
  return <section><h1>Alpha Components</h1><p>누적 수령액: 18,800 USDC</p><p>진행 중 인보이스: {items.filter((invoice) => invoice.status !== "SETTLED").length}</p><Link to="/supplier/invoices/new">새 인보이스 등록</Link><h2>인보이스 목록</h2>{items.length === 0 ? <EmptyState message="등록된 인보이스가 없습니다." /> : <ul>{items.map((invoice) => <li key={invoice.id}><Link to={`/supplier/invoices/${invoice.id}`}>{invoice.id}</Link> <StatusBadge status={invoice.status} /></li>)}</ul>}</section>;
}
