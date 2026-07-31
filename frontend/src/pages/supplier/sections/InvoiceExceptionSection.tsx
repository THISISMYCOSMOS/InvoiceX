import { ArrowCounterClockwise, Prohibit, WarningCircle } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import type { Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

const krwFormatter = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "KRW",
  maximumFractionDigits: 0,
});

type Tone = "danger" | "amber";

/** The reason the backend recorded, so the screen never says "blocked" with no cause. */
function failureReason(invoice: Invoice): string | undefined {
  const failed = [...invoice.agentTraces].reverse().find((trace) => trace.status === "FAILED");
  return failed?.summary;
}

export function InvoiceExceptionSection({ invoice }: { invoice: Invoice }) {
  const { language, t } = useLanguage();
  const localizedDateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });

  const reason = failureReason(invoice);
  const riskFactors = invoice.riskPassport?.riskFactors ?? [];

  const copy: Record<
    string,
    { tone: Tone; badge: string; title: string; body: string; next: string }
  > = {
    BLOCKED: {
      tone: "danger",
      badge: t("BLOCKED", "진행 불가"),
      title: t("This invoice cannot proceed", "이 인보이스는 진행할 수 없습니다"),
      body: t(
        "Early settlement was not issued. No USDC has been transferred.",
        "조기정산이 실행되지 않았습니다. USDC는 지급되지 않았습니다.",
      ),
      next: t(
        "Register a new invoice, or contact the buyer if you believe this is an error.",
        "새 인보이스를 등록하시거나, 잘못된 판정이라고 판단되면 구매기업에 문의하세요.",
      ),
    },
    REVISION_REQUESTED: {
      tone: "amber",
      badge: t("REVISION REQUESTED", "보완 요청됨"),
      title: t("The buyer asked for a correction", "구매기업이 보완을 요청했습니다"),
      body: t(
        "The buyer could not verify the submission as it stands.",
        "구매기업이 제출된 내용 그대로는 확인할 수 없다고 회신했습니다.",
      ),
      next: t(
        "Correct the documents and register the invoice again.",
        "문서를 보완한 뒤 인보이스를 다시 등록하세요.",
      ),
    },
    DISPUTED: {
      tone: "danger",
      badge: t("DISPUTED", "이의 제기됨"),
      title: t("The buyer raised a dispute", "구매기업이 이의를 제기했습니다"),
      body: t(
        "Early settlement is on hold until the dispute is resolved.",
        "이의가 해소될 때까지 조기정산이 보류됩니다.",
      ),
      next: t(
        "Resolve the dispute with the buyer before resubmitting.",
        "구매기업과 이의를 해소한 뒤 다시 제출하세요.",
      ),
    },
    ERROR: {
      tone: "danger",
      badge: t("PROCESSING ERROR", "처리 오류"),
      title: t("Processing stopped unexpectedly", "처리가 중단되었습니다"),
      body: t(
        "The invoice did not finish its last step.",
        "인보이스가 마지막 단계를 끝내지 못했습니다.",
      ),
      next: t(
        "Register the invoice again. If it keeps failing, report the reason below.",
        "인보이스를 다시 등록해 주세요. 계속 실패하면 아래 사유를 담당자에게 전달해 주세요.",
      ),
    },
  };

  const content = copy[invoice.status] ?? copy.ERROR;
  const Icon =
    invoice.status === "REVISION_REQUESTED"
      ? ArrowCounterClockwise
      : invoice.status === "ERROR"
        ? WarningCircle
        : Prohibit;

  return (
    <section className="invoice-exception">
      <p className="breadcrumb">{t("Invoices", "인보이스")} / {invoice.id}</p>
      <section className={`pending-card exception-card exception-card--${content.tone}`}>
        <span className="pending-card__icon exception-card__icon" aria-hidden="true">
          <Icon size={18} weight="bold" />
        </span>
        <span className="pending-badge exception-badge">{content.badge}</span>
        <h1>{content.title}</h1>
        <p>{content.body}</p>

        <dl className="pending-summary">
          <div>
            <dt>{t("Buyer", "구매기업")}</dt>
            <dd>{invoice.buyer.name}</dd>
          </div>
          <div>
            <dt>{t("Invoice amount", "인보이스 금액")}</dt>
            <dd>{krwFormatter.format(invoice.invoiceAmountKrw)}</dd>
          </div>
          <div>
            <dt>{t("Due date", "만기일")}</dt>
            <dd>{localizedDateFormatter.format(new Date(`${invoice.dueDate}T00:00:00`))}</dd>
          </div>
        </dl>

        {reason && (
          <div className="exception-reason">
            <strong>{t("Reason", "사유")}</strong>
            <span>{reason}</span>
          </div>
        )}

        {riskFactors.length > 0 && (
          <ul className="exception-factors" aria-label={t("Risk factors", "위험 요인")}>
            {riskFactors.map((factor) => (
              <li key={factor.title} className={`exception-factor exception-factor--${factor.severity.toLowerCase()}`}>
                <strong>{factor.title}</strong>
                <span>{factor.description}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="pending-notice">
          <strong>{t("What to do next", "다음 단계")}</strong>
          <span>{content.next}</span>
        </div>

        <footer className="exception-actions">
          <Link className="secondary-button" to="/supplier">
            {t("Back to invoices", "인보이스 목록으로")}
          </Link>
          <Link className="primary-button" to="/supplier/invoices/new">
            {t("Register a new invoice", "새 인보이스 등록")}
          </Link>
        </footer>
      </section>
    </section>
  );
}
