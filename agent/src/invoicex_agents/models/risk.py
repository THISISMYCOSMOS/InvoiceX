"""Structured input and output contracts for the Risk Agent."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from invoicex_agents.models.common import SourceEvidence, StrictModel


class RiskFactorContext(StrictModel):
    """A deterministic risk factor supplied by the backend policy engine."""

    code: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
    title: str = Field(min_length=1, max_length=200)
    facts: list[str] = Field(min_length=1)
    source_evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_evidence(self) -> RiskFactorContext:
        if len(self.source_evidence_ids) != len(set(self.source_evidence_ids)):
            raise ValueError("risk factor sourceEvidenceIds must be unique")
        return self


class RiskAnalysisRequest(StrictModel):
    """Buyer-confirmed, policy-derived context accepted by the Risk Agent."""

    invoice_id: str = Field(min_length=1, max_length=100)
    buyer_decision: Literal["CONFIRM"]
    risk_score: int = Field(ge=0, le=100)
    risk_level: str = Field(min_length=1, max_length=50)
    risk_factors: list[RiskFactorContext] = Field(min_length=1)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_factor_references(self) -> RiskAnalysisRequest:
        factor_codes = [factor.code for factor in self.risk_factors]
        if len(factor_codes) != len(set(factor_codes)):
            raise ValueError("risk factor codes must be unique")

        evidence_ids = [item.evidence_id for item in self.source_evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("sourceEvidence evidenceId values must be unique")
        known_evidence_ids = set(evidence_ids)

        for factor in self.risk_factors:
            if not set(factor.source_evidence_ids) <= known_evidence_ids:
                raise ValueError("risk factor references an unknown sourceEvidenceId")

        return self


class RiskNarrativeReason(StrictModel):
    """A grounded explanation of one backend-provided risk factor."""

    factor_code: str = Field(min_length=1, max_length=64)
    explanation: str = Field(min_length=1, max_length=1500)
    source_evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_evidence(self) -> RiskNarrativeReason:
        if len(self.source_evidence_ids) != len(set(self.source_evidence_ids)):
            raise ValueError("risk reason sourceEvidenceIds must be unique")
        return self


class RiskNarrative(StrictModel):
    """The only portion of risk output that Gemini is allowed to generate."""

    risk_reasons: list[RiskNarrativeReason] = Field(default_factory=list)
    review_required: bool
    risk_passport_summary: str = Field(min_length=1, max_length=2000)


class RiskPassport(StrictModel):
    """Backend-assembled passport preserving deterministic score and level."""

    invoice_id: str
    risk_score: int
    risk_level: str
    summary: str
    factor_codes: list[str]
    source_evidence_ids: list[str]


class RiskAnalysisResult(StrictModel):
    """Final Risk Agent result returned to the future backend."""

    schema_version: Literal["risk-agent.v1"] = "risk-agent.v1"
    invoice_id: str
    risk_score: int
    risk_level: str
    risk_factors: list[RiskFactorContext]
    risk_reasons: list[RiskNarrativeReason]
    source_evidence: list[SourceEvidence]
    review_required: bool
    risk_passport: RiskPassport
