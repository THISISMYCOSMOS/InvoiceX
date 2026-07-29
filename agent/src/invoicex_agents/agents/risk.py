"""Risk Agent orchestration with deterministic score preservation."""

from __future__ import annotations

from invoicex_agents.agents._prompts import load_prompt
from invoicex_agents.clients.base import StructuredOutputClient
from invoicex_agents.exceptions import GeminiResponseValidationError
from invoicex_agents.models.risk import (
    RiskAnalysisRequest,
    RiskAnalysisResult,
    RiskNarrative,
    RiskPassport,
)


class RiskAgent:
    """Explain backend-provided risk facts without changing financial decisions."""

    def __init__(self, client: StructuredOutputClient) -> None:
        self._client = client
        self._system_instruction = load_prompt("risk_agent.md")

    def analyze(self, request: RiskAnalysisRequest) -> RiskAnalysisResult:
        """Generate grounded explanations and assemble an immutable Risk Passport."""

        narrative = self._client.generate_structured(
            system_instruction=self._system_instruction,
            user_prompt=request.model_dump_json(by_alias=True),
            response_schema=RiskNarrative,
        )
        self._validate_narrative(request, narrative)

        evidence_ids = sorted(
            {
                evidence_id
                for factor in request.risk_factors
                for evidence_id in factor.source_evidence_ids
            }
        )
        factor_codes = [factor.code for factor in request.risk_factors]
        passport = RiskPassport(
            invoice_id=request.invoice_id,
            risk_score=request.risk_score,
            risk_level=request.risk_level,
            summary=narrative.risk_passport_summary,
            factor_codes=factor_codes,
            source_evidence_ids=evidence_ids,
        )
        return RiskAnalysisResult(
            invoice_id=request.invoice_id,
            risk_score=request.risk_score,
            risk_level=request.risk_level,
            risk_factors=request.risk_factors,
            risk_reasons=narrative.risk_reasons,
            source_evidence=request.source_evidence,
            review_required=narrative.review_required,
            risk_passport=passport,
        )

    @staticmethod
    def _validate_narrative(
        request: RiskAnalysisRequest,
        narrative: RiskNarrative,
    ) -> None:
        factor_by_code = {factor.code: factor for factor in request.risk_factors}
        output_codes = [reason.factor_code for reason in narrative.risk_reasons]

        if len(output_codes) != len(set(output_codes)):
            raise GeminiResponseValidationError("Risk Agent returned duplicate factor explanations")
        if set(output_codes) != set(factor_by_code):
            raise GeminiResponseValidationError(
                "Risk Agent must explain exactly the backend-provided risk factors"
            )

        for reason in narrative.risk_reasons:
            allowed_evidence = set(factor_by_code[reason.factor_code].source_evidence_ids)
            if not set(reason.source_evidence_ids) <= allowed_evidence:
                raise GeminiResponseValidationError(
                    "Risk Agent referenced evidence outside its risk factor"
                )
