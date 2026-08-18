import type { AgentActivityTimeline as Activity } from "../types/agents";
import { useLanguage } from "../i18n/LanguageContext";

export function AgentActivityTimeline({ activity }: { activity: Activity | null | undefined }) {
  const { t } = useLanguage();
  if (!activity || activity.timeline.length === 0) return null;
  return (
    <section className="agent-activity-timeline">
      <h2>{t("Agent activity", "에이전트 진행 기록")}</h2>
      <ol>
        {activity.timeline.map((item) => (
          <li key={item.id}>
            <strong>{item.title}</strong> <span>{item.status}</span>
            <p>{item.summary}</p>
            {item.methodVersion ? <small>Risk method: {item.methodVersion}</small> : null}
            {item.checks ? <small>{Object.entries(item.checks).map(([key, value]) => `${key}: ${value ? "PASS" : "FAIL"}`).join(" · ")}</small> : null}
            {item.explorerUrl && item.transactionSignature ? <a href={item.explorerUrl} target="_blank" rel="noreferrer">{item.transactionSignature}</a> : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
