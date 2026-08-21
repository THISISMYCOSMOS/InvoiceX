import { useState } from "react";
import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoice } from "../../hooks/useInvoice";
import { useAgentActivity } from "../../hooks/useAgentActivity";
import { AgentActivityTimeline } from "../../components/AgentActivityTimeline";
import { TransactionReceipt } from "../../components/TransactionReceipt";
import { useLanguage } from "../../i18n/LanguageContext";
import type { AgentActivityTimeline as AgentTimelineData } from "../../types/agents";
import { formatInvoiceAmount, type AgentDecision, type Invoice } from "../../types/invoice";
import { investorActivityResult } from "./investorActivityStatus";

interface PolicyCheck {
  label: string;
  passed: boolean;
}

function shortAddress(value: string): string {
  return value.length > 16 ? `${value.slice(0, 6)}…${value.slice(-6)}` : value;
}

function formatTimestamp(value: string | undefined, locale: string): string {
  if (!value) return "—";
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.valueOf())
    ? value
    : new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(timestamp);
}

function decisionCopy(
  decision: AgentDecision | undefined,
  t: (english: string, korean: string) => string,
): { heading: string; description: string; notice: string } {
  switch (decision?.status) {
    case "EXECUTED":
      return {
        heading: t("Treasury Agent decision", "Treasury Agent 투자 결정"),
        description: t(
          "The agent evaluated the signed mandate and executed this investment without transaction-level human approval.",
          "에이전트가 서명된 Mandate를 평가하고 건별 승인 없이 이 투자를 실행했습니다.",
        ),
        notice: t(
          "The agent selected and executed this investment within the institution-approved mandate.",
          "에이전트가 기관 승인 Mandate 범위 안에서 이 투자를 선택하고 실행했습니다.",
        ),
      };
    case "REJECTED":
      return {
        heading: t("Treasury Agent decision", "Treasury Agent 투자 결정"),
        description: decision.reason ?? t("The signed mandate did not approve this investment.", "서명된 Mandate가 이 투자를 승인하지 않았습니다."),
        notice: t("No on-chain purchase was sent.", "온체인 매수 트랜잭션은 전송되지 않았습니다."),
      };
    case "FAILED":
      return {
        heading: t("Treasury Agent execution failed", "Treasury Agent 실행 실패"),
        description: decision.reason ?? t("The mandate passed, but the on-chain purchase did not complete.", "Mandate는 통과했지만 온체인 매수가 완료되지 않았습니다."),
        notice: t("The invoice remains available for a safe retry after the issue is resolved.", "문제가 해결되면 인보이스를 안전하게 다시 실행할 수 있습니다."),
      };
    case "APPROVED":
      return {
        heading: t("Treasury Agent purchase in progress", "Treasury Agent 매수 처리 중"),
        description: t("The signed mandate approved this investment. The on-chain purchase is being confirmed.", "서명된 Mandate가 이 투자를 승인했습니다. 온체인 매수를 확인 중입니다."),
        notice: t("No further investor approval is required within the signed mandate.", "서명된 Mandate 범위 안에서는 추가 투자자 승인이 필요하지 않습니다."),
      };
    default:
      return {
        heading: t("Treasury Agent evaluation pending", "Treasury Agent 평가 대기"),
        description: decision?.reason ?? t("The RWA is waiting for an active mandate and sufficient Vault balance.", "RWA가 활성 Mandate와 충분한 Vault 잔액을 기다리고 있습니다."),
        notice: t("A purchase starts automatically when every signed-mandate check passes.", "서명된 Mandate의 모든 검증을 통과하면 매수가 자동으로 시작됩니다."),
      };
  }
}

function policyChecks(decision: AgentDecision | undefined, t: (english: string, korean: string) => string): PolicyCheck[] {
  const labels: Record<string, [string, string]> = {
    policyActive: ["Mandate active", "Mandate 활성"],
    riskEligible: ["Risk eligible", "위험 적격"],
    minimumRiskScore: ["Minimum Risk Score", "최소 위험 점수"],
    buyerAllowlist: ["Buyer allowlist", "구매기업 허용 목록"],
    maximumRemainingTerm: ["Maximum remaining term", "최대 잔존 만기"],
    perInvoiceLimit: ["Per-invoice limit", "인보이스별 한도"],
    totalInvestmentLimit: ["Total investment limit", "총 투자 한도"],
    vaultAvailableBalance: ["Vault available balance", "Vault 가용 잔액"],
  };

  return Object.entries(decision?.checks ?? {}).map(([key, passed]) => {
    const [english, korean] = labels[key] ?? [key, key];
    return { label: t(english, korean), passed };
  });
}

export function InvestorActivityContent({
  invoice,
  activity,
}: {
  invoice: Invoice;
  activity?: AgentTimelineData | null;
}) {
  const { t, language } = useLanguage();
  const [activeTab, setActiveTab] = useState<"summary" | "timeline">("summary");
  const decision = invoice.agentDecision;
  const checks = policyChecks(decision, t);
  const passedChecks = checks.filter((check) => check.passed).length;
  const investment = invoice.fundingTransaction?.amountUsdc ?? decision?.amountUsdc ?? 0;
  const transaction = invoice.fundingTransaction;
  const copy = decisionCopy(decision, t);
  const result = investorActivityResult(invoice);
  const rwaId = invoice.rwaAsset?.mintAddress;
  const settlementTransaction = invoice.investorPayoutTransaction ?? invoice.settlementTransaction;

  return (
    <section className="investor-decision">
      <p className="investor-breadcrumb">
        {t("Agent Activity", "에이전트 활동")} / {invoice.id}
      </p>

      <header className="investor-decision__heading">
        <div>
          <h1>{copy.heading}</h1>
          <p>{copy.description}</p>
        </div>
        <span>{checks.length > 0 ? `${passedChecks} / ${checks.length} ${t("PASSED", "통과")}` : t("PENDING", "대기")}</span>
      </header>

      <div className="investor-activity-tabs" role="tablist" aria-label={t("Investment activity views", "투자 활동 보기")}>
        <button
          id="investor-activity-summary-tab"
          className={activeTab === "summary" ? "is-active" : ""}
          role="tab"
          type="button"
          aria-selected={activeTab === "summary"}
          aria-controls="investor-activity-summary-panel"
          onClick={() => setActiveTab("summary")}
        >
          {t("Decision summary", "투자 결정")}
        </button>
        <button
          id="investor-activity-timeline-tab"
          className={activeTab === "timeline" ? "is-active" : ""}
          role="tab"
          type="button"
          aria-selected={activeTab === "timeline"}
          aria-controls="investor-activity-timeline-panel"
          aria-label={t("Agent timeline", "에이전트 진행 기록")}
          onClick={() => setActiveTab("timeline")}
        >
          {t("Agent timeline", "에이전트 진행 기록")}
          {activity?.timeline.length ? <span>{activity.timeline.length}</span> : null}
        </button>
      </div>

      {activeTab === "summary" ? (
        <div id="investor-activity-summary-panel" role="tabpanel" aria-labelledby="investor-activity-summary-tab">
          <div className="investor-decision__grid">
            <section className="investor-policy-card">
              <header>
                <h2>{t("Mandate evaluation", "Mandate 평가")}</h2>
                <time dateTime={decision?.createdAt}>{formatTimestamp(decision?.createdAt, language === "ko" ? "ko-KR" : "en-US")}</time>
              </header>
              <div className="investor-policy-grid">
                {checks.length > 0 ? checks.map((check) => (
                  <article key={check.label}>
                    <div>
                      <span>{check.label}</span>
                      <b>{check.passed ? t("PASS", "통과") : t("NOT MET", "미충족")}</b>
                    </div>
                    <strong>{check.passed ? t("Within mandate", "Mandate 충족") : t("Outside mandate", "Mandate 미충족")}</strong>
                  </article>
                )) : (
                  <p className="investor-activity-empty">{t("No mandate evaluation has been recorded yet.", "아직 기록된 Mandate 평가가 없습니다.")}</p>
                )}
              </div>
            </section>

            <div className="investor-execution-column">
              <section className="investor-execution-card">
                <header>
                  <h2>{t("Execution summary", "실행 요약")}</h2>
                </header>
                <dl>
                  <div><dt>{t("RWA mint", "RWA 민트")}</dt><dd title={rwaId}>{rwaId ? shortAddress(rwaId) : "—"}</dd></div>
                  <div><dt>{t("Investment", "투자 금액")}</dt><dd>{investment.toLocaleString("en-US")} USDC</dd></div>
                  <div><dt>{t("Risk Score", "위험 점수")}</dt><dd>{invoice.riskPassport?.riskScore ?? "—"}{invoice.riskPassport?.riskScore !== null && invoice.riskPassport?.riskScore !== undefined ? " / 100" : ""}</dd></div>
                  <div><dt>{t("Decision", "결정")}</dt><dd>{t(result.english, result.korean)}</dd></div>
                  <div>
                    <dt>{t("Transaction", "트랜잭션")}</dt>
                    <dd>{transaction ? <a href={transaction.explorerUrl} target="_blank" rel="noreferrer">{shortAddress(transaction.signature)}</a> : "—"}</dd>
                  </div>
                </dl>
                {transaction ? (
                  <a
                    className="investor-primary-button investor-position-button"
                    href={transaction.explorerUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("View RWA position", "RWA 포지션 보기")}
                  </a>
                ) : null}
              </section>
              <p className="investor-agent-notice">{copy.notice}</p>
            </div>
          </div>

          {invoice.status === "SETTLED" && invoice.settlement ? (
            <section className="investor-settlement">
              <header>
                <div>
                  <span>{t("MATURITY SETTLED", "만기 정산 완료")}</span>
                  <h2>{t("Maturity settlement received", "투자자 만기 수령 완료")}</h2>
                </div>
                <strong>{t("CONFIRMED", "확인 완료")}</strong>
              </header>
              <dl>
                <div><dt>{t("RWA face value", "RWA 액면가")}</dt><dd>{formatInvoiceAmount(invoice.settlement.invoiceFaceValueUsdc, "USDC")}</dd></div>
                <div><dt>{t("Investor settlement", "투자자 만기 수령액")}</dt><dd>{formatInvoiceAmount(invoice.settlement.investorSettlementUsdc, "USDC")}</dd></div>
                <div><dt>{t("Platform fee", "플랫폼 수수료")}</dt><dd>{formatInvoiceAmount(invoice.settlement.platformFeeUsdc, "USDC")}</dd></div>
              </dl>
              {settlementTransaction ? <TransactionReceipt transaction={settlementTransaction} /> : null}
            </section>
          ) : null}
        </div>
      ) : (
        <div id="investor-activity-timeline-panel" role="tabpanel" aria-labelledby="investor-activity-timeline-tab">
          <AgentActivityTimeline activity={activity} />
        </div>
      )}
    </section>
  );
}

export function InvestorActivityPage() {
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const invoice = useInvoice(invoiceId);
  const activity = useAgentActivity(invoiceId, "Investor");

  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) {
    return (
      <ErrorState
        error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))}
      />
    );
  }

  return <InvestorActivityContent invoice={invoice.data} activity={activity.data} />;
}
