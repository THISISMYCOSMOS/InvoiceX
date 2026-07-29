import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { AgentTraceList } from "../../components/AgentTraceList";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";

export function InvestorDashboardPage() {
  const dashboard = useInvestorDashboard();
  if (dashboard.isLoading) return <LoadingState />;
  if (dashboard.error || !dashboard.data) return <ErrorState error={dashboard.error ?? new Error("투자기관 정보를 찾을 수 없습니다.")} />;
  const data = dashboard.data;
  return <section><h1>{data.investorName}</h1><p>자동투자 활성 여부: {data.automatedInvestmentActive ? "활성" : "비활성"}</p><p>AP2 Mandate 상태: {data.mandateStatus}</p><p>Vault 투자 가능 잔액: {data.availableVaultUsdc} USDC</p><p>미상환 투자원금: {data.outstandingPrincipalUsdc} USDC</p><AgentTraceList traces={data.recentAgentTraces} /></section>;
}
