import { Plus } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { rwaApi } from "../../api/rwa.api";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { getInvoiceDisplayReference, useInvoices } from "../../hooks/useInvoices";
import { useDevnetUsdcBalance } from "../../hooks/useDevnetUsdcBalance";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatInvoiceAmount } from "../../types/invoice";
import { useCurrentPrivyAccount } from "../../auth/currentAccount";
import { getDashboardSummary } from "./supplierDashboardSummary";

export function SupplierDashboardPage() {
  const invoices = useInvoices();
  const { language, t } = useLanguage();
  const currentAccount = useCurrentPrivyAccount();
  const settlementWallet = useQuery({
    queryKey: [
      "auth",
      "settlement-wallet",
      currentAccount?.userEmail,
      currentAccount?.walletAddress,
    ],
    queryFn: () => rwaApi.getSettlementWallet(),
    enabled: Boolean(currentAccount),
    gcTime: 0,
    refetchOnMount: "always",
  });
  const settlementWalletAddress = (
    settlementWallet.data
      && currentAccount
      && settlementWallet.data.embeddedWalletAddress === currentAccount.walletAddress
      ? settlementWallet.data.address
      : currentAccount?.walletAddress
  );
  const supplierWalletBalance = useDevnetUsdcBalance(settlementWalletAddress);
  if (invoices.isLoading) return <LoadingState />;
  if (invoices.error) return <ErrorState error={invoices.error} />;
  const items = invoices.data ?? [];
  const summary = getDashboardSummary(items, settlementWalletAddress);
  const usdcFormatter = new Intl.NumberFormat(language === "ko" ? "ko-KR" : "en-US", {
    maximumFractionDigits: 6,
  });
  const dateFormatter = new Intl.DateTimeFormat(language === "ko" ? "ko-KR" : "en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
  const statusLabel = (status: string) => {
    const labels: Record<string, [string, string]> = {
      DOCUMENT_REVIEW_REQUIRED: ["Review extraction", "추출 정보 확인"],
      BUYER_REVIEW: ["Buyer review", "구매기업 검증"],
      BUYER_VERIFIED: ["Buyer verified", "구매기업 검증 완료"],
      RISK_ASSESSING: ["Preparing offer", "조기정산 제안 준비 중"],
      OFFER_READY: ["Buyer verified", "구매기업 확인 완료"],
      REVIEW_REQUESTED: ["Review Requested", "Review Requested"],
      RWA_ISSUED: ["RWA issued", "RWA 발행 완료"],
      FUNDING: ["Funding in progress", "조기정산 진행 중"],
      FUNDED: ["Funded", "정산 완료"],
      SETTLED: ["Settled", "상환 완료"],
    };
    const [english, korean] = labels[status] ?? [status.replaceAll("_", " "), status.replaceAll("_", " ")];
    return language === "ko" ? korean : english;
  };
  const statusTone = (status: string) => {
    if (status === "DOCUMENT_REVIEW_REQUIRED" || status === "BUYER_REVIEW" || status === "OFFER_READY" || status === "REVIEW_REQUESTED" || status === "RWA_ISSUED") return "blue";
    if (status === "FUNDING" || status === "RISK_ASSESSING") return "amber";
    if (status === "FUNDED" || status === "SETTLED") return "green";
    return "slate";
  };
  const contactName = currentAccount?.userName?.trim() || (language === "ko" ? "민준" : "Minjun");

  return (
    <section className="supplier-dashboard">
      <header className="page-heading">
        <div>
          <h1>{language === "ko" ? `좋은 아침이에요, ${contactName}님` : `Good morning, ${contactName}`}</h1>
          <p>{t("Track invoices and access working capital faster.", "인보이스를 관리하고 운용자금을 더 빠르게 확보하세요.")}</p>
        </div>
        <Link className="primary-button compact-button" to="/supplier/invoices/new">
          <Plus aria-hidden="true" size={14} weight="bold" />
          {t("New invoice", "새 인보이스")}
        </Link>
      </header>

      <div className="dashboard-stats">
        <section className="stat-card" aria-label={t("USDC wallet balance", "USDC 지갑 잔액")}>
          <span>{t("USDC wallet balance", "USDC 지갑 잔액")}</span>
          <strong>
            {supplierWalletBalance.isLoading
              ? "…"
              : supplierWalletBalance.balanceUsdc === null
                ? "—"
                : usdcFormatter.format(supplierWalletBalance.balanceUsdc)} <small>USDC</small>
          </strong>
          <p>{supplierWalletBalance.address
            ? supplierWalletBalance.isError
              ? t("Unable to load balance", "잔액을 불러오지 못했습니다")
              : t("Connected wallet", "연결된 정산 지갑")
            : t("Connect a settlement wallet", "정산 지갑을 연결해 주세요")}</p>
        </section>
        <section className="stat-card" aria-label={t("In early settlement", "조기정산 진행 중")}>
          <span>{t("In early settlement", "조기정산 진행 중")}</span>
          <strong>{summary.earlySettlementInProgress} <small>{t("invoices", "건")}</small></strong>
        </section>
        <section className="stat-card" aria-label={t("Waiting for buyer", "구매자 응답 대기")}>
          <span>{t("Waiting for buyer", "구매자 응답 대기")}</span>
          <strong>{summary.waitingForBuyer} <small>{t("requests", "건")}</small></strong>
        </section>
        <section className="stat-card" aria-label={t("Received by current wallet", "현재 지갑 수령액")}>
          <span>{t("Received by current wallet", "현재 지갑 수령액")}</span>
          <strong>{summary.settlementReceivedUsdc.toLocaleString()} <small>USDC</small></strong>
        </section>
      </div>

      <section className="recent-invoices">
        <header>
          <h2>{t("Recent invoices", "최근 인보이스")}</h2>
          <Link className="secondary-button" to="/supplier/invoices/new">{t("View all", "전체 보기")}</Link>
        </header>
        {items.length === 0 ? (
          <EmptyState message={t("No invoices have been registered.", "등록된 인보이스가 없습니다.")} />
        ) : (
          <div className="table-scroll">
            <table aria-label={t("Recent invoices", "최근 인보이스")}>
              <thead>
                <tr>
                  <th>{t("Invoice", "인보이스")}</th>
                  <th>{t("Buyer", "구매자")}</th>
                  <th>{t("Amount", "금액")}</th>
                  <th>{t("Due date", "만기일")}</th>
                  <th>{t("Status", "상태")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((invoice) => (
                  <tr key={invoice.id}>
                    <td>
                      <Link to={`/supplier/invoices/${invoice.id}`} aria-label={t(`View invoice ${getInvoiceDisplayReference(invoice)}`, `${getInvoiceDisplayReference(invoice)} 상세 보기`)}>
                        {getInvoiceDisplayReference(invoice)}
                      </Link>
                    </td>
                    <td>{invoice.buyer.name}</td>
                    <td>{formatInvoiceAmount(invoice.invoiceAmount, invoice.currency, language === "ko" ? "ko-KR" : "en-US")}</td>
                    <td>{dateFormatter.format(new Date(`${invoice.dueDate}T00:00:00`))}</td>
                    <td><span className={`dashboard-status dashboard-status--${statusTone(invoice.status)}`}>{statusLabel(invoice.status)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
