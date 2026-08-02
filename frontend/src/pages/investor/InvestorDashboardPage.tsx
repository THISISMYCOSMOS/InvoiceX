import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";
import { useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";

const usdc = new Intl.NumberFormat("en-US");

function activityResult(invoice: { agentDecision?: { status: string } }) {
  switch (invoice.agentDecision?.status) {
    case "EXECUTED": return { english: "Invested", korean: "투자 완료", className: "investor-result--invested" };
    case "REJECTED": return { english: "Not approved", korean: "미승인", className: "investor-result--excluded" };
    case "FAILED": return { english: "Execution failed", korean: "실행 실패", className: "investor-result--excluded" };
    case "APPROVED": return { english: "Executing", korean: "실행 중", className: "investor-result--invested" };
    default: return { english: "Awaiting mandate", korean: "Mandate 대기", className: "investor-result--excluded" };
  }
}

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
  const firstActivityInvoice = activityInvoices[0];
  const stats = [
    {
      label: t("Available to invest", "투자 가능 금액"),
      value: data.availableVaultUsdc,
      unit: "USDC",
    },
    {
      label: t("Outstanding principal", "미상환 투자 원금"),
      value: data.outstandingPrincipalUsdc,
      unit: "USDC",
    },
    {
      label: t("Due within 30 days", "30일 이내 만기"),
      value: data.dueWithin30DaysUsdc,
      unit: "USDC",
    },
    {
      label: t("Needs attention", "확인 필요 건"),
      value: data.attentionRequiredCount,
      unit: t("cases", "건"),
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
          <h1>{t("Treasury overview", "자금 운용 현황")}</h1>
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
        <Link className="investor-primary-button" to="/investor/setup">
          {t("Manage mandate", "투자 위임 관리")}
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
          <h2>{t("Recent Treasury Agent activity", "최근 Treasury Agent 활동")}</h2>
          <Link className="investor-secondary-button" to={firstActivityInvoice ? `/investor/activities/${firstActivityInvoice.id}` : "/investor"}>
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
              {activityInvoices.length > 0 ? activityInvoices.map((invoice) => {
                const result = activityResult(invoice);
                const amount = invoice.fundingTransaction?.amountUsdc ?? invoice.agentDecision?.amountUsdc ?? 0;
                const activityTime = invoice.fundingTransaction?.createdAt ?? invoice.agentDecision?.createdAt;
                return (
                  <tr key={invoice.id}>
                  <td>
                    <Link to={`/investor/activities/${invoice.id}`}>
                      {invoice.id}
                    </Link>
                  </td>
                  <td>{invoice.buyer.name}</td>
                  <td>
                    <span className={`investor-result ${result.className}`}>{t(result.english, result.korean)}</span>
                  </td>
                  <td className="is-strong">{usdc.format(amount)} USDC</td>
                  <td>{activityTime ? new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(activityTime)) : "—"}</td>
                </tr>
                );
              }) : (
                <tr><td colSpan={5} className="investor-activity-empty">{t("No investment has been executed yet.", "아직 실행된 투자가 없습니다.")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
