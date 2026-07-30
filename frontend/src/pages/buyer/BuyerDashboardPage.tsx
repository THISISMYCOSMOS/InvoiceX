import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoices } from "../../hooks/useInvoices";

const fallbackRequests = [
  {
    id: "INV-2026-001",
    supplier: "Alpha Components",
    amountKrw: 20_000_000,
    dueDate: "Oct 30, 2026",
    primary: true,
  },
  {
    id: "INV-2026-018",
    supplier: "Hanul Parts",
    amountKrw: 31_200_000,
    dueDate: "Nov 05, 2026",
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
        <h1>Invoice verification</h1>
        <p>Review supplier invoices and manage upcoming payments.</p>
      </header>

      <div className="buyer-stats" aria-label="Buyer invoice summary">
        <article>
          <span>New requests</span>
          <strong>3 <small>invoices</small></strong>
        </article>
        <article>
          <span>Due in 30 days</span>
          <strong>₩68.4M</strong>
        </article>
        <article>
          <span>Completed this month</span>
          <strong>12</strong>
        </article>
      </div>

      <section className="buyer-request-card">
        <header>
          <h2>New verification requests</h2>
          <button type="button" className="secondary-button buyer-view-all">View all</button>
        </header>
        <div className="table-scroll">
          <table aria-label="New verification requests">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Supplier</th>
                <th>Amount</th>
                <th>Due date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.id}>
                  <td><strong>{request.id}</strong></td>
                  <td>{request.supplier}</td>
                  <td>{krw.format(request.amountKrw)}</td>
                  <td>{request.dueDate}</td>
                  <td>
                    <Link
                      className={request.primary ? "buyer-review-link is-primary" : "buyer-review-link"}
                      to={`/buyer/invoices/${request.id}?section=verification`}
                      aria-label={`Review ${request.id}`}
                    >
                      Review
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
