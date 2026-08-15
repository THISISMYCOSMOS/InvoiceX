import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoices } from "../../hooks/useInvoices";
import { useLanguage } from "../../i18n/LanguageContext";
import { type InvestorActivityFilter, investorActivityAmount, investorActivityReason, investorActivityResult, investorActivityTime } from "./investorActivityStatus";
import { useState } from "react";

const filters: InvestorActivityFilter[] = ["ALL", "EXECUTED", "NOT_EXECUTED", "IN_REVIEW"];

export function InvestorActivityListPage() {
  const invoices = useInvoices();
  const { t, language } = useLanguage();
  const [filter, setFilter] = useState<InvestorActivityFilter>("ALL");

  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error || !invoices.data) {
    return <ErrorState error={invoices.error ?? new Error(t("Agent activities could not be loaded.", "Agent 활동을 불러오지 못했습니다."))} />;
  }

  const activities = [...invoices.data
    .filter((invoice) => Boolean(invoice.agentDecision || invoice.rwaAsset))
    .filter((invoice) => filter === "ALL" || investorActivityResult(invoice).filter === filter)]
    .sort((first, second) => {
      const firstTime = investorActivityTime(first) ?? "";
      const secondTime = investorActivityTime(second) ?? "";
      return secondTime.localeCompare(firstTime);
    });
  const filterLabel = (value: InvestorActivityFilter) => {
    switch (value) {
      case "EXECUTED": return t("Investment executed", "투자 실행");
      case "NOT_EXECUTED": return t("Investment not executed", "투자 보류");
      case "IN_REVIEW": return t("Under review", "검토 중");
      default: return t("All", "전체");
    }
  };
  const dateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", { dateStyle: "medium", timeStyle: "short" });

  return (
    <section className="investor-dashboard investor-activity-list-page">
      <header className="investor-page-heading">
        <div>
          <p className="investor-breadcrumb">{t("Investor / Agent Activity", "투자자 / 에이전트 활동")}</p>
          <h1>{t("Agent Activity", "에이전트 활동")}</h1>
          <p>{t("Review every Treasury Agent investment decision and open its Mandate evaluation.", "Treasury Agent의 모든 투자 판단을 확인하고 Mandate 평가 상세를 열어보세요.")}</p>
        </div>
      </header>

      <div className="investor-activity-filters" role="group" aria-label={t("Filter Agent Activity", "에이전트 활동 필터")}>
        {filters.map((value) => (
          <button key={value} type="button" className={filter === value ? "is-active" : ""} aria-pressed={filter === value} onClick={() => setFilter(value)}>
            {filterLabel(value)}
          </button>
        ))}
      </div>

      <section className="investor-activity-card">
        <header>
          <h2>{t("Treasury Agent decisions", "Treasury Agent 투자 판단")}</h2>
          <span>{t(`${activities.length} decisions`, `${activities.length}건`)}</span>
        </header>
        <div className="table-scroll">
          <table aria-label={t("Treasury Agent decisions", "Treasury Agent 투자 판단")}>
            <thead><tr><th>{t("Invoice", "인보이스")}</th><th>{t("Buyer", "구매기업")}</th><th>{t("Decision", "결정")}</th><th>{t("Reason", "핵심 사유")}</th><th>{t("Amount", "금액")}</th><th>{t("Time", "시간")}</th></tr></thead>
            <tbody>
              {activities.length > 0 ? activities.map((invoice) => {
                const result = investorActivityResult(invoice);
                const time = investorActivityTime(invoice);
                return (
                  <tr key={invoice.id}>
                    <td><Link to={`/investor/activities/${invoice.id}`}>{invoice.id}</Link></td>
                    <td>{invoice.buyer.name}</td>
                    <td><span className={`investor-result ${result.className}`}>{t(result.english, result.korean)}</span></td>
                    <td className="investor-activity-reason">{investorActivityReason(invoice, t("Mandate conditions passed.", "Mandate 조건을 통과했습니다."), t("Mandate evaluation is in progress.", "Mandate 평가를 진행 중입니다."))}</td>
                    <td className="is-strong">{investorActivityAmount(invoice).toLocaleString()} USDC</td>
                    <td>{time ? dateFormatter.format(new Date(time)) : "—"}</td>
                  </tr>
                );
              }) : <tr><td colSpan={6} className="investor-activity-empty">{t("No Agent decisions match this filter.", "선택한 조건에 해당하는 Agent 판단이 없습니다.")}</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
