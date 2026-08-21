import { ArrowSquareOut, CheckCircle, FileText } from "@phosphor-icons/react";
import { formatInvoiceAmount, type Invoice } from "../../../types/invoice";
import { useLanguage } from "../../../i18n/LanguageContext";

export function RwaIssuedSection({ invoice }: { invoice: Invoice }) {
  const { language, t } = useLanguage();
  const amount = invoice.riskPassport?.suggestedAdvanceAmountUsdc;
  const faceValueUsdc = invoice.rwaAsset?.faceValueUsdc ?? invoice.riskPassport?.invoiceFaceValueUsdc;
  const purchasePriceUsdc = invoice.rwaAsset?.purchasePriceUsdc
    ?? invoice.rwaAsset?.issuancePriceUsdc
    ?? amount;
  const dateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
  const advanceRate = invoice.riskPassport?.suggestedAdvanceRateBps;
  const issueTransaction = invoice.rwaAsset?.issueTransaction;
  const shortenAddress = (address?: string) => {
    if (!address) return "—";
    return address.length > 18 ? `${address.slice(0, 8)}...${address.slice(-6)}` : address;
  };
  const issuedAt = issueTransaction?.createdAt
    ? new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
      month: "short",
      day: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(issueTransaction.createdAt))
    : "—";

  return (
    <section className="rwa-issued">
      <article className="rwa-issued-card">
        <header>
          <span className="rwa-issued-card__icon" aria-hidden="true"><CheckCircle size={25} weight="fill" /></span>
          <div>
            <span className="rwa-issued-card__eyebrow">{t("RWA ISSUED", "RWA 발행 완료")}</span>
            <h1>{t("Your invoice RWA has been issued", "인보이스 RWA가 발행되었습니다")}</h1>
            <p>{t(
              "Your verified invoice has been issued as an RWA. Settlement updates will appear on this page.",
              "구매기업 확인을 마친 인보이스가 RWA로 발행되었습니다. 정산 진행 상황은 이 페이지에서 확인할 수 있습니다.",
            )}</p>
          </div>
          <span className="rwa-issued-card__badge"><CheckCircle size={13} weight="fill" aria-hidden="true" /> {t("ISSUED", "발행 완료")}</span>
        </header>
        <div className="rwa-issued-card__body">
          <section className="rwa-issued-card__group">
            <h2>{t("Invoice details", "인보이스 정보")}</h2>
            <dl>
              <div><dt>{t("Invoice ID", "인보이스 ID")}</dt><dd>{invoice.id}</dd></div>
              <div><dt>{t("Supplier", "공급기업")}</dt><dd>{invoice.supplier.name}</dd></div>
              <div><dt>{t("Buyer", "구매기업")}</dt><dd>{invoice.buyer.name}</dd></div>
              <div><dt>{t("Invoice amount", "인보이스 금액")}</dt><dd>{formatInvoiceAmount(invoice.invoiceAmount, invoice.currency, language === "ko" ? "ko-KR" : "en-US")}</dd></div>
              <div><dt>{t("Issue date", "발행일")}</dt><dd>{dateFormatter.format(new Date(`${invoice.issueDate}T00:00:00`))}</dd></div>
              <div><dt>{t("Delivery date", "납품일")}</dt><dd>{dateFormatter.format(new Date(`${invoice.deliveryDate}T00:00:00`))}</dd></div>
              <div><dt>{t("Due date", "만기일")}</dt><dd>{dateFormatter.format(new Date(`${invoice.dueDate}T00:00:00`))}</dd></div>
              <div><dt>{t("Contract number", "계약 번호")}</dt><dd>{invoice.contractNumber}</dd></div>
              <div><dt>{t("Purchase order number", "발주 번호")}</dt><dd>{invoice.purchaseOrderNumber}</dd></div>
            </dl>
          </section>
          <section className="rwa-issued-card__group">
            <h2>Risk Passport</h2>
            <dl>
              <div><dt>{t("Eligibility", "적격 여부")}</dt><dd>{invoice.riskPassport?.eligibility ?? "—"}</dd></div>
              <div><dt>{t("Risk Passport score", "Risk Passport 점수")}</dt><dd>{invoice.riskPassport?.riskScore ?? "—"}{invoice.riskPassport?.riskScore !== null && invoice.riskPassport?.riskScore !== undefined ? " / 100" : ""}</dd></div>
              <div><dt>{t("Advance rate", "조기정산 비율")}</dt><dd>{advanceRate === null || advanceRate === undefined ? "—" : `${advanceRate / 100}%`}</dd></div>
              <div><dt>{t("RWA face value", "RWA 기준 채권가치")}</dt><dd>{faceValueUsdc === undefined || faceValueUsdc === null ? "—" : formatInvoiceAmount(faceValueUsdc, "USDC")}</dd></div>
              <div><dt>{t("RWA purchase price", "RWA 매입가")}</dt><dd>{purchasePriceUsdc === undefined || purchasePriceUsdc === null ? "—" : formatInvoiceAmount(purchasePriceUsdc, "USDC")}</dd></div>
              <div><dt>{t("Supplier settlement", "공급기업 정산액")}</dt><dd>{amount === undefined || amount === null ? "—" : formatInvoiceAmount(amount, "USDC")}</dd></div>
              <div><dt>{t("Policy version", "정책 버전")}</dt><dd>{invoice.riskPassport?.policyVersion ?? "—"}</dd></div>
              <div><dt>{t("Analysis documents", "분석 문서")}</dt><dd>{invoice.documents.length} {t("files", "개")}</dd></div>
            </dl>
          </section>
          <section className="rwa-issued-card__group">
            <h2>{t("RWA asset details", "RWA 자산 정보")}</h2>
            <dl>
              <div><dt>{t("Issuance status", "RWA 발행 상태")}</dt><dd>{t("Issued", "발행 완료")}</dd></div>
              <div><dt>{t("Asset status", "자산 상태")}</dt><dd>{invoice.rwaAsset?.status ?? "—"}</dd></div>
              <div><dt>{t("RWA mint", "RWA 민트")}</dt><dd title={invoice.rwaAsset?.mintAddress}>{shortenAddress(invoice.rwaAsset?.mintAddress)}</dd></div>
              <div><dt>{t("Escrow account", "에스크로 계정")}</dt><dd title={invoice.rwaAsset?.escrowTokenAccount}>{shortenAddress(invoice.rwaAsset?.escrowTokenAccount)}</dd></div>
              <div><dt>{t("Current owner Vault", "현재 보유 Vault")}</dt><dd title={invoice.rwaAsset?.ownerVaultAddress}>{shortenAddress(invoice.rwaAsset?.ownerVaultAddress)}</dd></div>
              <div><dt>{t("Issued at", "발행 시각")}</dt><dd>{issuedAt}</dd></div>
              <div><dt>{t("Issue transaction", "발행 트랜잭션")}</dt><dd title={issueTransaction?.signature}>{shortenAddress(issueTransaction?.signature)}</dd></div>
            </dl>
          </section>
        </div>
        <div className="rwa-issued-card__notice">
          <span><FileText size={18} weight="fill" aria-hidden="true" /></span>
          <p>{t("The issued RWA is held safely in platform escrow. Settlement updates will appear here.", "발행된 RWA는 플랫폼 에스크로에 안전하게 보관됩니다. 정산 진행 상황은 이 페이지에서 확인할 수 있습니다.")}</p>
        </div>
        {issueTransaction?.explorerUrl && (
          <a className="rwa-issued-card__explorer-link" href={issueTransaction.explorerUrl} target="_blank" rel="noreferrer">
            <ArrowSquareOut size={16} weight="bold" aria-hidden="true" />
            {t("View issuance on Solana Explorer", "Explorer에서 온체인 기록 보기")}
          </a>
        )}
      </article>
    </section>
  );
}
