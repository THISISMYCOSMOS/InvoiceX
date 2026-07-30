import { useParams } from "react-router-dom";
import { AgentTraceList } from "../../components/AgentTraceList";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { RiskPassportSummary } from "../../components/RiskPassportSummary";
import { TransactionReceipt } from "../../components/TransactionReceipt";
import { useInvoice } from "../../hooks/useInvoice";
import type { Invoice } from "../../types/invoice";
import { useLanguage } from "../../i18n/LanguageContext";

export function InvestorActivityContent({ invoice }: { invoice: Invoice }) {
  const { t } = useLanguage();
  return <section><h1>{invoice.id} {t("Investment activity", "투자 활동")}</h1>{invoice.riskPassport && <RiskPassportSummary passport={invoice.riskPassport} />}<h2>{t("Investment policy verification", "투자 정책 검증 결과")}</h2><p>{t("Eligible — Buyer Allowlist and minimum Risk Score requirements are satisfied.", "적격 — Buyer Allowlist와 최소 Risk Score를 충족했습니다.")}</p><h2>{t("AP2 verification", "AP2 검증 결과")}</h2><p>{t("The demo Mandate is active.", "데모 Mandate가 활성 상태입니다.")}</p><AgentTraceList traces={invoice.agentTraces} />{invoice.fundingTransaction && <TransactionReceipt transaction={invoice.fundingTransaction} />}{invoice.settlement && <p>{t("Settlement result: investor", "Settlement 결과: 투자기관")} {invoice.settlement.investorSettlementUsdc} USDC</p>}</section>;
}

export function InvestorActivityPage() {
  const { t } = useLanguage();
  const { invoiceId = "" } = useParams();
  const invoice = useInvoice(invoiceId);
  if (invoice.isLoading) return <LoadingState />;
  if (invoice.error || !invoice.data) return <ErrorState error={invoice.error ?? new Error(t("Invoice not found.", "인보이스를 찾을 수 없습니다."))} />;
  return <InvestorActivityContent invoice={invoice.data} />;
}
