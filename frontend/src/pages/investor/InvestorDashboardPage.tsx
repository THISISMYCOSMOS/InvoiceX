import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";
import { useInvoices } from "../../hooks/useInvoices";
import { useRwaPurchase } from "../../hooks/useRwaPurchase";
import { useLanguage } from "../../i18n/LanguageContext";

const usdc = new Intl.NumberFormat("en-US");

export function InvestorDashboardPage() {
  const dashboard = useInvestorDashboard();
  const invoices = useInvoices();
  const purchaseRwa = useRwaPurchase();
  const { t } = useLanguage();

  if (dashboard.isLoading) return <LoadingState />;
  if (dashboard.error || !dashboard.data) {
    return (
      <ErrorState
        error={dashboard.error ?? new Error(t(
          "Investor information not found.",
          "투자자 정보를 찾을 수 없습니다.",
        ))}
      />
    );
  }

  const data = dashboard.data;
  const purchaseOpportunities = invoices.data?.filter((invoice) => invoice.status === "RWA_ISSUED") ?? [];
  const fundedInvoices = invoices.data?.filter((invoice) => invoice.status === "FUNDED" || invoice.status === "SETTLED") ?? [];
  const stats = [
    {
      label: t("Available to invest", "투자 가능 금액"),
      value: data.availableVaultUsdc,
    },
    {
      label: t("Outstanding principal", "미상환 투자 원금"),
      value: data.outstandingPrincipalUsdc,
    },
    {
      label: t("Due within 30 days", "30일 이내 만기"),
      value: data.dueWithin30DaysUsdc ?? 72_840,
    },
  ];

  return (
    <section className="investor-dashboard">
      <header className="investor-page-heading">
        <div>
          <h1>{t("Treasury overview", "자금 운용 현황")}</h1>
          <p>
            {t(
              "Monitor available capital, outstanding positions, and exceptions requiring action.",
              "투자 가능 자금, 미상환 포지션과 조치가 필요한 예외 항목을 확인하세요.",
            )}
          </p>
        </div>
        <Link className="investor-primary-button" to="/investor/setup">
          {t("Manage mandate", "투자 위임 관리")}
        </Link>
      </header>

      <div className="investor-stats" aria-label={t("Treasury summary", "자금 운용 요약")}>
        {stats.map((stat) => (
          <article key={stat.label}>
            <span>{stat.label}</span>
            <strong>
              {usdc.format(stat.value)} <small>USDC</small>
            </strong>
          </article>
        ))}
      </div>

      <section className="investor-purchase-card">
        <header>
          <div>
            <span>{t("RWA PURCHASE OPPORTUNITIES", "RWA 매수 가능 자산")}</span>
            <h2>{t("Issued RWAs awaiting investment", "투자 대기 중인 발행 RWA")}</h2>
          </div>
          <p>{t("Purchase triggers the USDC transfer to the supplier settlement wallet.", "매수 완료 시 공급기업 정산 지갑으로 USDC가 지급됩니다.")}</p>
        </header>
        {purchaseOpportunities.length > 0 ? (
          <div className="investor-purchase-list">
            {purchaseOpportunities.map((invoice) => {
              const amount = invoice.riskPassport?.suggestedAdvanceAmountUsdc ?? 0;
              return (
                <article key={invoice.id} className="investor-purchase-row">
                  <div>
                    <Link to={`/investor/activities/${invoice.id}`}>{invoice.id}</Link>
                    <strong>{invoice.buyer.name}</strong>
                  </div>
                  <dl>
                    <div><dt>{t("RWA", "RWA")}</dt><dd>RWA-{invoice.id}</dd></div>
                    <div><dt>{t("Investment", "투자 금액")}</dt><dd>{usdc.format(amount)} USDC</dd></div>
                    <div><dt>{t("Risk score", "위험 점수")}</dt><dd>{invoice.riskPassport?.riskScore ?? "—"} / 100</dd></div>
                  </dl>
                  <button
                    type="button"
                    className="investor-primary-button"
                    disabled={purchaseRwa.isPending}
                    onClick={() => purchaseRwa.mutate(invoice.id)}
                  >
                    {purchaseRwa.isPending ? t("Purchasing…", "매수 처리 중…") : t("Purchase RWA", "RWA 매수")}
                  </button>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="investor-purchase-empty">
            {t("There are no issued RWAs awaiting investment.", "현재 투자 대기 중인 발행 RWA가 없습니다.")}
          </div>
        )}
        {purchaseRwa.error && <p className="investor-purchase-error">{t("RWA purchase could not be completed. Please try again.", "RWA 매수를 완료하지 못했습니다. 다시 시도해 주세요.")}</p>}
      </section>

      <section className="investor-activity-card">
        <header>
          <h2>{t("Recent Treasury Agent activity", "최근 Treasury Agent 활동")}</h2>
          <Link className="investor-secondary-button" to="/investor/activities/INV-2026-001">
            {t("View all", "전체 보기")}
          </Link>
        </header>
        <div className="table-scroll">
          <table aria-label={t("Recent Treasury Agent activity", "최근 Treasury Agent 활동")}>
            <thead>
              <tr>
                <th>{t("Invoice", "인보이스")}</th>
                <th>{t("Buyer", "구매기업")}</th>
                <th>{t("Result", "결과")}</th>
                <th>{t("Amount", "금액")}</th>
                <th>{t("Time", "시간")}</th>
              </tr>
            </thead>
            <tbody>
              {fundedInvoices.length > 0 ? fundedInvoices.map((invoice) => (
                <tr key={invoice.id}>
                  <td>
                    <Link to={`/investor/activities/${invoice.id}`}>
                      {invoice.id}
                    </Link>
                  </td>
                  <td>{invoice.buyer.name}</td>
                  <td>
                    <span className="investor-result investor-result--invested">{t("Invested", "투자 완료")}</span>
                  </td>
                  <td className="is-strong">{usdc.format(invoice.fundingTransaction?.amountUsdc ?? 0)} USDC</td>
                  <td>{t("Completed", "완료")}</td>
                </tr>
              )) : (
                <tr><td colSpan={5} className="investor-activity-empty">{t("No investment has been executed yet.", "아직 실행된 투자가 없습니다.")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
