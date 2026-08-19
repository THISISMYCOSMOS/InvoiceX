import { ArrowsClockwise } from "@phosphor-icons/react";
import { InvoiceRegistrationProgress } from "../../../components/InvoiceRegistrationProgress";
import { formatInvoiceAmount, type Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

export function BuyerReviewPendingSection({ invoice }: { invoice: Invoice }) {
  const { language, t } = useLanguage();
  const localizedDateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
  return (
    <section className="buyer-review-pending">
      <p className="breadcrumb">{t("Invoices", "인보이스")} / {invoice.id}</p>
      <InvoiceRegistrationProgress step={3} />
      <section className="pending-card">
        <span className="pending-card__icon" aria-hidden="true">
          <ArrowsClockwise size={18} weight="bold" />
        </span>
        <span className="pending-badge">{t("BUYER REVIEW", "구매자 검토")}</span>
        <h1>{t("Waiting for buyer verification", "구매자 검증 대기 중")}</h1>
        <p>{t(
          `${invoice.buyer.name} is reviewing the invoice amount, due date, and proof of delivery.`,
          `${invoice.buyer.name}에서 인보이스 금액, 만기일, 납품 증빙을 검토하고 있습니다.`,
        )}</p>

        <dl className="pending-summary">
          <div>
            <dt>{t("Buyer", "구매자")}</dt>
            <dd>{invoice.buyer.name}</dd>
          </div>
          <div>
            <dt>{t("Invoice amount", "인보이스 금액")}</dt>
            <dd>{formatInvoiceAmount(invoice.invoiceAmount, invoice.currency, language === "ko" ? "ko-KR" : "en-US")}</dd>
          </div>
          <div>
            <dt>{t("Due date", "만기일")}</dt>
            <dd>{localizedDateFormatter.format(new Date(`${invoice.dueDate}T00:00:00`))}</dd>
          </div>
        </dl>

        <div className="pending-notice">
          <strong>{t("Verification requested · Jul 29, 2026 · 10:42", "검증 요청 · 2026년 7월 29일 · 10:42")}</strong>
          <span>{t("We'll notify you when the buyer completes verification.", "구매자가 검증을 완료하면 알려드리겠습니다.")}</span>
        </div>
      </section>
    </section>
  );
}
