"""Run one real Risk Agent call with non-sensitive synthetic inputs."""

from invoicex_agents import AgentSettings, GoogleGeminiClient, RiskAgent
from invoicex_agents.models import (
    RiskAnalysisRequest,
    RiskFactorContext,
    SourceEvidence,
)


def main() -> None:
    """Generate and print a validated narrative for backend-owned risk facts."""

    request = RiskAnalysisRequest(
        invoice_id="INV-TEST-001",
        buyer_decision="CONFIRM",
        risk_score=86,
        risk_level="POLICY_ACCEPTABLE",
        risk_factors=[
            RiskFactorContext(
                code="DOCUMENT_MATCH",
                title="Buyer-confirmed document match",
                facts=[
                    "The buyer confirmed the invoice.",
                    "The invoice number and total amount are supported by the supplied invoice.",
                ],
                source_evidence_ids=["ev-invoice-number", "ev-total-amount"],
            )
        ],
        source_evidence=[
            SourceEvidence(
                evidence_id="ev-invoice-number",
                document_id="synthetic-invoice-1",
                page=1,
                field="invoiceNumber",
                quote="Invoice Number: INV-TEST-001",
            ),
            SourceEvidence(
                evidence_id="ev-total-amount",
                document_id="synthetic-invoice-1",
                page=1,
                field="totalAmount",
                quote="Total Amount: 20,000,000 KRW",
            ),
        ],
    )
    result = RiskAgent(GoogleGeminiClient(AgentSettings())).analyze(request)
    print(result.model_dump_json(by_alias=True, indent=2))


if __name__ == "__main__":
    main()
