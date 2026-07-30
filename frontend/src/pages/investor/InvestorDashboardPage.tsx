import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { AgentTraceList } from "../../components/AgentTraceList";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";
import { useLanguage } from "../../i18n/LanguageContext";

export function InvestorDashboardPage() {
  const dashboard = useInvestorDashboard();
  const { t } = useLanguage();
  if (dashboard.isLoading) return <LoadingState />;
  if (dashboard.error || !dashboard.data) return <ErrorState error={dashboard.error ?? new Error(t("Investor information not found.", "투자기관 정보를 찾을 수 없습니다."))} />;
  const data = dashboard.data;
  return <section><h1>{data.investorName}</h1><p>{t("Automated investment", "자동투자 활성 여부")}: {data.automatedInvestmentActive ? t("Active", "활성") : t("Inactive", "비활성")}</p><p>{t("AP2 Mandate status", "AP2 Mandate 상태")}: {data.mandateStatus}</p><p>{t("Available Vault balance", "Vault 투자 가능 잔액")}: {data.availableVaultUsdc} USDC</p><p>{t("Outstanding principal", "미상환 투자원금")}: {data.outstandingPrincipalUsdc} USDC</p><AgentTraceList traces={data.recentAgentTraces} /></section>;
}
