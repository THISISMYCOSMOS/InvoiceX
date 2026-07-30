import type { AgentTrace } from "../types/agents";
import { useLanguage } from "../i18n/LanguageContext";

export function AgentTraceList({ traces }: { traces: AgentTrace[] }) {
  const { t } = useLanguage();
  return <section><h2>{t("Agent trace", "에이전트 추적")}</h2><ul>{traces.map((trace) => <li key={trace.id}><strong>{trace.sourceAgent.replace("_", " ")} → {trace.targetAgent.replace("_", " ")}</strong><br />{trace.summary}</li>)}</ul></section>;
}
