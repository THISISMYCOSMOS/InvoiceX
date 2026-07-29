import type { AgentTrace } from "../types/agents";

export function AgentTraceList({ traces }: { traces: AgentTrace[] }) {
  return <section><h2>Agent Trace</h2><ul>{traces.map((trace) => <li key={trace.id}>{trace.sourceAgent.replace("_", " ")} → {trace.targetAgent.replace("_", " ")}<br />{trace.summary}</li>)}</ul></section>;
}
