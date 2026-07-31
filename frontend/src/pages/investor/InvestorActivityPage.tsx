import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoice } from "../../hooks/useInvoice";
import { useLanguage } from "../../i18n/LanguageContext";
import type { Invoice, InvestorMandate } from "../../types/invoice";
import { useInvestorDashboard } from "../../hooks/useInvestorDashboard";
import { useInvestorMandate } from "../../hooks/useInvestorMandate";

interface PolicyCheck {
  label: string;
  value: string;
  passed: boolean;
}

const usdc = new Intl.NumberFormat("en-US");

function daysUntil(dueDate: string): number {
  const due = new Date(`${dueDate}T00:00:00`).getTime();
  return Math.max(Math.ceil((due - Date.now()) / 86_400_000), 0);
}

export function InvestorActivityContent({
  invoice,
  mandate,
  availableVaultUsdc,
}: {
  invoice: Invoice;
  mandate: InvestorMandate;
  availableVaultUsdc: number;
}) {
  const { language, t } = useLanguage();
  const riskScore = invoice.riskPassport?.riskScore;
  const investment = invoice.fundingTransaction?.amountUsdc ?? 0;
  const transactionUrl = invoice.fundingTransaction?.explorerUrl;
  const remainingDays = daysUntil(invoice.dueDate);
  const signature = invoice.fundingTransaction?.signature;
  const shortSignature = signature
    ? `${signature.slice(0, 4)}...${signature.slice(-4)}`
    : "-";
  const decidedAt = invoice.fundingTransaction
    ? new Date(invoice.fundingTransaction.createdAt)
    : undefined;
  const decidedLabel = decidedAt
    ? new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(decidedAt)
    : "";
  // Every row mirrors a rule TreasuryMandatePolicy actually enforces.
  const policyChecks: PolicyCheck[] = [
    {
      label: t("Buyer allowlist", "구매기업 허용 목록"),
      value: invoice.buyer.name,
      passed: mandate.buyerAllowlist.includes(invoice.buyer.id),
    },
    {
      label: t("Minimum Risk Score", "최소 위험 점수"),
      value: `${riskScore ?? "-"} ≥ ${mandate.minimumRiskScore}`,
      passed: riskScore !== null && riskScore !== undefined && riskScore >= mandate.minimumRiskScore,
    },
    {
      label: t("Max amount / invoice", "인보이스당 최대 금액"),
      value: `${usdc.format(investment)} ≤ ${usdc.format(mandate.perInvoiceLimitUsdc)}`,
      passed: investment <= mandate.perInvoiceLimitUsdc,
    },
    {
      label: t("Remaining maturity", "잔존 만기"),
      value: t(
        `${remainingDays} days ≤ ${mandate.maximumTermDays} days`,
        `${remainingDays}일 ≤ ${mandate.maximumTermDays}일`,
      ),
      passed: remainingDays <= mandate.maximumTermDays,
    },
    {
      label: t("Vault available balance", "Vault 가용 잔액"),
      value: `${usdc.format(availableVaultUsdc)} USDC`,
      passed: availableVaultUsdc >= 0,
    },
  ];
  const passedCount = policyChecks.filter((check) => check.passed).length;

  return (
    <section className="investor-decision">
      <p className="investor-breadcrumb">
        {t("Agent Activity", "에이전트 활동")} / {invoice.id}
      </p>

      <header className="investor-decision__heading">
        <div>
          <h1>{t("Treasury Agent decision", "Treasury Agent 투자 결정")}</h1>
          <p>
            {t(
              "A deterministic mandate check approved this investment without transaction-level human approval.",
              "결정론적 위임 정책 검증을 통해 건별 승인 없이 투자가 승인되었습니다.",
            )}
          </p>
        </div>
        <span>{t(`${passedCount} / ${policyChecks.length} PASSED`, `${passedCount} / ${policyChecks.length} 통과`)}</span>
      </header>

      <div className="investor-decision__grid">
        <section className="investor-policy-card">
          <header>
            <h2>{t("Mandate evaluation · Policy v1.4", "위임 정책 평가 · Policy v1.4")}</h2>
            {decidedAt && (
              <time dateTime={decidedAt.toISOString()}>{decidedLabel}</time>
            )}
          </header>
          <div className="investor-policy-grid">
            {policyChecks.map((check) => (
              <article key={check.label}>
                <div>
                  <span>{check.label}</span>
                  <b>{check.passed ? t("PASS", "통과") : t("FAIL", "실패")}</b>
                </div>
                <strong>{check.value}</strong>
              </article>
            ))}
          </div>
        </section>

        <div className="investor-execution-column">
          <section className="investor-execution-card">
            <header>
              <h2>{t("Execution summary", "실행 요약")}</h2>
            </header>
            <dl>
              <div><dt>{t("RWA ID", "RWA ID")}</dt><dd>RWA-INV-001</dd></div>
              <div><dt>{t("Investment", "투자 금액")}</dt><dd>{investment.toLocaleString("en-US")} USDC</dd></div>
              <div><dt>{t("Risk Score", "위험 점수")}</dt><dd>{riskScore ?? "-"} / 100</dd></div>
              <div><dt>Treasury Agent</dt><dd>v0.9.2</dd></div>
              <div>
                <dt>{t("Transaction", "트랜잭션")}</dt>
                <dd><a href={transactionUrl} target="_blank" rel="noreferrer">{shortSignature}</a></dd>
              </div>
            </dl>
            <a
              className="investor-primary-button investor-position-button"
              href={transactionUrl}
              target="_blank"
              rel="noreferrer"
            >
              {t("View RWA position", "RWA 포지션 보기")}
            </a>
          </section>
          <p className="investor-agent-notice">
            {t(
              "The agent selected and executed this investment within the institution-approved mandate.",
              "에이전트가 기관 승인 위임 범위 안에서 이 투자를 선택하고 실행했습니다.",
            )}
          </p>
        </div>
      </div>
    </section>
  );
}

export function InvestorActivityPage() {
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const invoice = useInvoice(invoiceId);
  const dashboard = useInvestorDashboard();
  const { mandate } = useInvestorMandate();

  if (invoice.isLoading || dashboard.isLoading || mandate.isLoading) return <LoadingState />;
  if (
    invoice.error || !invoice.data
    || dashboard.error || !dashboard.data
    || mandate.error || !mandate.data
  ) {
    return (
      <ErrorState
        error={
          invoice.error ?? dashboard.error ?? mandate.error
          ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))
        }
      />
    );
  }

  return (
    <InvestorActivityContent
      invoice={invoice.data}
      mandate={mandate.data}
      availableVaultUsdc={dashboard.data.availableVaultUsdc}
    />
  );
}
