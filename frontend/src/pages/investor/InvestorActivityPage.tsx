import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { useInvoice } from "../../hooks/useInvoice";
import { useLanguage } from "../../i18n/LanguageContext";
import type { Invoice } from "../../types/invoice";

interface PolicyCheck {
  label: string;
  value: string;
}

export function InvestorActivityContent({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  const riskScore = invoice.riskPassport?.riskScore ?? 86;
  const investment = invoice.fundingTransaction?.amountUsdc ?? 18_800;
  const transactionUrl = invoice.fundingTransaction?.explorerUrl
    ?? "https://explorer.solana.com/tx/5igDemoFundingSignature?cluster=devnet";
  const policyChecks: PolicyCheck[] = [
    { label: t("Buyer allowlist", "구매기업 허용 목록"), value: invoice.buyer.name },
    { label: t("Minimum Risk Score", "최소 위험 점수"), value: `${riskScore} ≥ 80` },
    { label: t("Max amount / invoice", "인보이스당 최대 금액"), value: `${investment.toLocaleString("en-US")} ≤ 25,000` },
    { label: t("Remaining maturity", "잔존 만기"), value: t("45 days ≤ 90 days", "45일 ≤ 90일") },
    { label: t("Buyer concentration", "구매기업 집중도"), value: "18.7% ≤ 20%" },
    { label: t("Vault available balance", "Vault 가용 잔액"), value: "331,200 USDC" },
  ];

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
        <span>{t("6 / 6 PASSED", "6 / 6 통과")}</span>
      </header>

      <div className="investor-decision__grid">
        <section className="investor-policy-card">
          <header>
            <h2>{t("Mandate evaluation · Policy v1.4", "위임 정책 평가 · Policy v1.4")}</h2>
            <time dateTime="2026-07-30T14:32:00+09:00">
              {t("Jul 30, 2026 · 14:32", "2026년 7월 30일 · 14:32")}
            </time>
          </header>
          <div className="investor-policy-grid">
            {policyChecks.map((check) => (
              <article key={check.label}>
                <div>
                  <span>{check.label}</span>
                  <b>{t("PASS", "통과")}</b>
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
              <div><dt>{t("Risk Score", "위험 점수")}</dt><dd>{riskScore} / 100</dd></div>
              <div><dt>Treasury Agent</dt><dd>v0.9.2</dd></div>
              <div>
                <dt>{t("Transaction", "트랜잭션")}</dt>
                <dd><a href={transactionUrl} target="_blank" rel="noreferrer">4pYh...9kL2</a></dd>
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

  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) {
    return (
      <ErrorState
        error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))}
      />
    );
  }

  return <InvestorActivityContent invoice={invoice.data} />;
}
