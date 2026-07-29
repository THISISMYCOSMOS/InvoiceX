"""Risk Agent boundary and grounding tests."""

from typing import Any

import pytest
from pydantic import ValidationError

from invoicex_agents.agents.risk import RiskAgent
from invoicex_agents.clients.mock import StaticGeminiClient
from invoicex_agents.exceptions import GeminiResponseValidationError
from invoicex_agents.models.risk import RiskAnalysisRequest


def test_risk_agent_preserves_backend_score_and_level(
    valid_risk_request_data: dict[str, Any],
    valid_risk_narrative: dict[str, Any],
) -> None:
    request = RiskAnalysisRequest.model_validate(valid_risk_request_data)
    result = RiskAgent(StaticGeminiClient(valid_risk_narrative)).analyze(request)

    assert result.risk_score == 86
    assert result.risk_level == "POLICY_ACCEPTABLE"
    assert result.risk_passport.risk_score == 86
    assert result.risk_passport.factor_codes == ["DOCUMENT_MATCH"]


def test_risk_agent_rejects_unprovided_factor(
    valid_risk_request_data: dict[str, Any],
    valid_risk_narrative: dict[str, Any],
    copy_dict: Any,
) -> None:
    narrative = copy_dict(valid_risk_narrative)
    narrative["riskReasons"][0]["factorCode"] = "HALLUCINATED_FRAUD"
    request = RiskAnalysisRequest.model_validate(valid_risk_request_data)

    with pytest.raises(GeminiResponseValidationError, match="exactly"):
        RiskAgent(StaticGeminiClient(narrative)).analyze(request)


def test_risk_agent_rejects_cross_factor_evidence(
    valid_risk_request_data: dict[str, Any],
    valid_risk_narrative: dict[str, Any],
    copy_dict: Any,
) -> None:
    request_data = copy_dict(valid_risk_request_data)
    request_data["sourceEvidence"].append(
        {
            "evidenceId": "ev-other",
            "documentId": "invoice-1",
            "page": 1,
            "field": "buyerDecision",
            "quote": "Confirmed",
        }
    )
    narrative = copy_dict(valid_risk_narrative)
    narrative["riskReasons"][0]["sourceEvidenceIds"] = ["ev-other"]
    request = RiskAnalysisRequest.model_validate(request_data)

    with pytest.raises(GeminiResponseValidationError, match="outside"):
        RiskAgent(StaticGeminiClient(narrative)).analyze(request)


def test_risk_request_rejects_unconfirmed_buyer(
    valid_risk_request_data: dict[str, Any],
    copy_dict: Any,
) -> None:
    request_data = copy_dict(valid_risk_request_data)
    request_data["buyerDecision"] = "DISPUTE"

    with pytest.raises(ValidationError):
        RiskAnalysisRequest.model_validate(request_data)


def test_risk_request_rejects_unknown_evidence(
    valid_risk_request_data: dict[str, Any],
    copy_dict: Any,
) -> None:
    request_data = copy_dict(valid_risk_request_data)
    request_data["riskFactors"][0]["sourceEvidenceIds"] = ["not-present"]

    with pytest.raises(ValidationError, match="unknown"):
        RiskAnalysisRequest.model_validate(request_data)
