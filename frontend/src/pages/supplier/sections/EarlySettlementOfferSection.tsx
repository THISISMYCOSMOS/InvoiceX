import type { Invoice } from "../../../types/invoice";

export function EarlySettlementOfferSection({
  invoice,
  onAccept,
  onDecline = () => undefined,
}: {
  invoice: Invoice;
  onAccept: () => void;
  onDecline?: () => void;
}) {
  const score = invoice.riskPassport?.riskScore ?? 86;
  const advanceRate = (invoice.riskPassport?.suggestedAdvanceRateBps ?? 9_400) / 100;

  return (
    <section className="early-offer">
      <header className="early-offer__heading">
        <div>
          <p className="detail-breadcrumb">Invoices / {invoice.id} / Early settlement offer</p>
          <h1>Your early settlement offer is ready</h1>
          <p>Review the Risk Passport, expected proceeds, and fees before requesting RWA issuance.</p>
        </div>
        <span className="offer-ready-chip">OFFER READY</span>
      </header>

      <div className="early-offer__grid">
        <section className="risk-score-card">
          <span className="low-risk-chip">LOW RISK</span>
          <strong>{score}</strong>
          <small>/100</small>
          <h2>Invoice Risk Score</h2>
          <p>Buyer verification and payment history support this score.</p>
          <dl>
            <div><dt>Buyer verified</dt><dd>Passed</dd></div>
            <div><dt>Company KYB</dt><dd>Passed</dd></div>
            <div><dt>Duplicate signal</dt><dd>None</dd></div>
            <div><dt>Prior late payments</dt><dd>1 of 24</dd></div>
          </dl>
        </section>

        <section className="offer-proceeds-column">
          <article className="offer-proceeds-card">
            <span className="expected-proceeds-chip">EXPECTED PROCEEDS</span>
            <h2>18,800 USDC</h2>
            <p>Estimated using the hackathon mock rate of ₩1,000 / USDC.</p>
            <dl>
              <div><dt>Invoice amount</dt><dd>₩20,000,000</dd></div>
              <div><dt>Advance rate</dt><dd>{advanceRate}%</dd></div>
              <div><dt>Platform fee</dt><dd>200 USDC</dd></div>
              <div><dt>Estimated total early settlement cost</dt><dd>1,200 USDC</dd></div>
              <div><dt>Payment method</dt><dd>USDC · 8xK2...p91Q</dd></div>
            </dl>
          </article>
          <p className="offer-disclosure">
            Funds are paid after an eligible investor&apos;s Treasury Agent purchases the RWA. Matching is not guaranteed.
          </p>
          <footer className="offer-actions">
            <button type="button" className="secondary-button" onClick={onDecline}>Decline offer</button>
            <button type="button" className="primary-button" onClick={onAccept}>Accept &amp; request RWA issuance</button>
          </footer>
        </section>
      </div>
    </section>
  );
}
