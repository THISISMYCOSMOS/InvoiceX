import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";
import { useLanguage } from "../../i18n/LanguageContext";

/**
 * Sample feed rows. The live numbers a demo actually produces are the stat
 * tiles above, which come from the dashboard API; this table stays populated so
 * the screen does not look empty with a single invoice.
 */
const demoActivityRows = [
  {
    invoiceId: "INV-2026-001",
    buyer: "Prime Mobility",
    result: "invested",
    amount: "18,800 USDC",
    time: "14:32",
  },
  {
    invoiceId: "INV-2026-021",
    buyer: "Global Retail",
    result: "excluded",
    amount: "Risk 74",
    time: "14:18",
  },
] as const;

const usdc = new Intl.NumberFormat("en-US");

export function InvestorDashboardPage() {
  const dashboard = useInvestorDashboard();
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
      value: data.dueWithin30DaysUsdc ?? 0,
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
              {demoActivityRows.map((activity) => (
                <tr key={activity.invoiceId}>
                  <td>
                    <Link to={`/investor/activities/${activity.invoiceId}`}>
                      {activity.invoiceId}
                    </Link>
                  </td>
                  <td>{activity.buyer}</td>
                  <td>
                    <span className={`investor-result investor-result--${activity.result}`}>
                      {activity.result === "invested"
                        ? t("Invested", "투자 완료")
                        : t("Excluded", "제외")}
                    </span>
                  </td>
                  <td className={activity.result === "invested" ? "is-strong" : ""}>
                    {activity.result === "excluded" ? t("Risk 74", "위험도 74") : activity.amount}
                  </td>
                  <td>{activity.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
