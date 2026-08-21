import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";
import { useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";
import { investorActivityAmount, investorActivityResult, investorActivityTime } from "./investorActivityStatus";

const usdc = new Intl.NumberFormat("en-US", { maximumFractionDigits: 6 });

export function InvestorDashboardPage() {
  const dashboard = useInvestorDashboard();
  const invoices = useInvoices();
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
  const activityInvoices = invoices.data?.filter((invoice) => (
    Boolean(invoice.agentDecision || invoice.rwaAsset)
  )) ?? [];
  const automatedInvestmentInvoices = activityInvoices.filter((invoice) => (
    invoice.agentDecision?.status === "EXECUTED"
    && (invoice.rwaAsset?.status === "SOLD" || invoice.rwaAsset?.status === "SETTLED")
  ));
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const overdueReceivables = automatedInvestmentInvoices.filter((invoice) => {
    if (invoice.status === "SETTLED") return false;
    const dueDate = new Date(`${invoice.dueDate}T00:00:00`);
    return !Number.isNaN(dueDate.getTime()) && dueDate < today;
  });
  const recentActivityInvoices = activityInvoices.slice(0, 3);
  const stats = [
    {
      label: t("Available to invest", "투자 가능 금액"),
      value: data.availableVaultUsdc,
      unit: "USDC",
    },
    {
      label: t("Total profit", "총 수익"),
      value: data.totalProfitUsdc,
      unit: "USDC",
    },
    {
      label: t("Auto-invested RWA", "자동 투자 RWA"),
      value: data.automatedInvestmentCount,
      unit: t("invoices", "건"),
    },
    {
      label: t("Overdue receivables", "연체 미수금"),
      value: overdueReceivables.length,
      unit: t("invoices", "건"),
    },
  ];
  const automatedInvestmentLabel = data.automatedInvestmentActive
    ? t("Auto-invest active", "자동투자 활성")
    : t("Auto-invest inactive", "자동투자 비활성");
  const mandateStatusLabel = data.mandateStatus === "ACTIVE"
    ? t("Mandate active", "Mandate 활성")
    : t("Mandate draft", "Mandate 초안");

  return (
    <section className="investor-dashboard">
      <header className="investor-page-heading">
        <div>
          <h1>{t("Dashboard", "Dashboard")}</h1>
          <p>
            {t(
              "Monitor available capital, outstanding positions, and exceptions requiring action.",
              "투자 가능 자금, 미상환 포지션과 조치가 필요한 예외 항목을 확인하세요.",
            )}
          </p>
          <span className={`investor-setup-draft ${data.automatedInvestmentActive ? "is-active" : ""}`}>
            {automatedInvestmentLabel} · {mandateStatusLabel}
          </span>
        </div>
        <Link className="investor-primary-button" to="/investor/investment-policy">
          {t("Manage Investment Policy", "Investment Policy 관리")}
        </Link>
      </header>

      <div className="investor-stats" aria-label={t("Treasury summary", "자금 운용 요약")}>
        {stats.map((stat) => (
          <article key={stat.label}>
            <span>{stat.label}</span>
            <strong>
              {usdc.format(stat.value)} <small>{stat.unit}</small>
            </strong>
          </article>
        ))}
      </div>

      <section className="investor-activity-card">
        <header>
          <h2>{t("Recent Agent decisions", "최근 Agent 투자 판단")}</h2>
          <Link className="investor-secondary-button" to="/investor/activities">
            {t("View all Agent Activity", "전체 Agent Activity 보기")}
          </Link>
        </header>
        <div className="table-scroll">
          <table aria-label={t("Recent Agent decisions", "최근 Agent 투자 판단")}>
            <thead>
              <tr>
                <th>{t("Invoice", "인보이스")}</th>
                <th>{t("Decision", "결정")}</th>
                <th>{t("Amount", "금액")}</th>
                <th>{t("Time", "시간")}</th>
              </tr>
            </thead>
            <tbody>
              {recentActivityInvoices.length > 0 ? recentActivityInvoices.map((invoice) => {
                const result = investorActivityResult(invoice);
                const amount = investorActivityAmount(invoice);
                const activityTime = investorActivityTime(invoice);
                return (
                  <tr key={invoice.id}>
                  <td>
                    <Link to={`/investor/activities/${invoice.id}`}>
                      {invoice.id}
                    </Link>
                  </td>
                  <td>
                    <span className={`investor-result ${result.className}`}>{t(result.english, result.korean)}</span>
                  </td>
                  <td className="is-strong">{usdc.format(amount)} USDC</td>
                  <td>{activityTime ? new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(activityTime)) : "—"}</td>
                </tr>
                );
              }) : (
                <tr><td colSpan={4} className="investor-activity-empty">{t("No Agent decisions yet. Review all activity when decisions begin.", "아직 Agent 투자 판단이 없습니다. 판단이 시작되면 전체 Agent Activity에서 확인할 수 있습니다.")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
