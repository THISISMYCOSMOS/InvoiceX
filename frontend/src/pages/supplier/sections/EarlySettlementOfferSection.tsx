import { RiskPassportSummary } from "../../../components/RiskPassportSummary";
import type { Invoice } from "../../../types/invoice";

export function EarlySettlementOfferSection({ invoice, onAccept }: { invoice: Invoice; onAccept: () => void }) {
  return <section>{invoice.riskPassport && <RiskPassportSummary passport={invoice.riskPassport} />}<p>예상 수령액: 18,800 USDC</p><p>조기정산 비용: 1,200 USDC</p><button type="button" onClick={onAccept}>조건 동의 및 조기정산 신청</button></section>;
}
