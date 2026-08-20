import { ArrowSquareOut, CheckCircle, CircleNotch, WarningCircle } from "@phosphor-icons/react";
import type { AgentActivityItem, AgentActivityTimeline as Activity } from "../types/agents";
import { useLanguage } from "../i18n/LanguageContext";

function activityTone(status: string): "complete" | "working" | "failed" {
  const normalized = status.toUpperCase();
  if (normalized === "FAILED" || normalized === "REJECTED") return "failed";
  if (normalized === "WORKING" || normalized === "SUBMITTED" || normalized === "PENDING") return "working";
  return "complete";
}

function ActivityIcon({ item }: { item: AgentActivityItem }) {
  const tone = activityTone(item.status);
  if (tone === "failed") return <WarningCircle aria-hidden="true" weight="fill" />;
  if (tone === "working") return <CircleNotch aria-hidden="true" weight="bold" />;
  return <CheckCircle aria-hidden="true" weight="fill" />;
}

function formatActivityTimestamp(value: string, locale: string): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.valueOf())) return value;
  return new Intl.DateTimeFormat(locale, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(timestamp);
}

export function AgentActivityTimeline({ activity }: { activity: Activity | null | undefined }) {
  const { t, language } = useLanguage();
  if (!activity || activity.timeline.length === 0) {
    return <p className="agent-activity-empty">{t("No agent activity has been recorded yet.", "아직 에이전트 진행 기록이 없습니다.")}</p>;
  }
  return (
    <section className="agent-activity-timeline">
      <header className="agent-activity-timeline__header">
        <div>
          <span>{t("Agent workflow", "에이전트 워크플로우")}</span>
          <h2>{t("Execution timeline", "실행 타임라인")}</h2>
        </div>
        <p>{t(`${activity.timeline.length} recorded steps`, `${activity.timeline.length}개 단계 기록`)}</p>
      </header>
      <ol>
        {activity.timeline.map((item) => (
          <li key={item.id} className={`agent-activity-timeline__item agent-activity-timeline__item--${activityTone(item.status)}`}>
            <span className="agent-activity-timeline__marker"><ActivityIcon item={item} /></span>
            <article>
              <header>
                <div>
                  <span className="agent-activity-timeline__type">{item.kind}</span>
                  <h3>{item.title}</h3>
                </div>
                <div className="agent-activity-timeline__meta">
                  <time dateTime={item.createdAt}>{formatActivityTimestamp(item.createdAt, language === "ko" ? "ko-KR" : "en-US")}</time>
                  <b>{item.status}</b>
                </div>
              </header>
              <p>{item.summary}</p>
              <div className="agent-activity-timeline__details">
                {item.methodVersion ? <span>{t("Method", "분석 방식")}: {item.methodVersion}</span> : null}
                {item.checks ? Object.entries(item.checks).map(([key, value]) => <span key={key} className={value ? "is-pass" : "is-fail"}>{key}: {value ? "PASS" : "FAIL"}</span>) : null}
                {item.explorerUrl && item.transactionSignature ? <a href={item.explorerUrl} target="_blank" rel="noreferrer">{item.transactionSignature}<ArrowSquareOut aria-hidden="true" /></a> : null}
              </div>
            </article>
          </li>
        ))}
      </ol>
    </section>
  );
}
