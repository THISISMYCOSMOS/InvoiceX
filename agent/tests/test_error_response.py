"""Sanitized public error response tests."""

from typing import Any

import pytest
from pydantic import ValidationError

from invoicex_agents.error_response import AgentErrorCode, build_agent_error_response
from invoicex_agents.exceptions import (
    AgentConfigurationError,
    AgentInputError,
    GeminiInvocationError,
    GeminiResponseValidationError,
)
from invoicex_agents.models.risk import RiskAnalysisRequest


@pytest.mark.parametrize(
    ("error", "code", "retryable"),
    [
        (
            AgentConfigurationError("secret config detail"),
            AgentErrorCode.AGENT_NOT_CONFIGURED,
            False,
        ),
        (AgentInputError("private document detail"), AgentErrorCode.INVALID_DOCUMENT, False),
        (
            GeminiInvocationError(
                "provider detail",
                status_code=503,
                retryable=True,
            ),
            AgentErrorCode.AI_TEMPORARILY_UNAVAILABLE,
            True,
        ),
        (
            GeminiInvocationError(
                "provider detail",
                status_code=403,
                retryable=False,
            ),
            AgentErrorCode.AI_REQUEST_FAILED,
            False,
        ),
        (
            GeminiResponseValidationError("invalid model payload"),
            AgentErrorCode.AI_RESPONSE_INVALID,
            True,
        ),
        (RuntimeError("unexpected private detail"), AgentErrorCode.ANALYSIS_FAILED, False),
    ],
)
def test_internal_errors_map_to_sanitized_responses(
    error: Exception,
    code: AgentErrorCode,
    retryable: bool,
) -> None:
    response = build_agent_error_response(error)
    serialized = response.model_dump_json(by_alias=True)

    assert response.schema_version == "agent-error.v1"
    assert response.status == "FAILED"
    assert response.error.code is code
    assert response.error.retryable is retryable
    assert str(error) not in serialized


def test_unconfirmed_buyer_has_stable_public_error(
    valid_risk_request_data: dict[str, Any],
    copy_dict: Any,
) -> None:
    request_data = copy_dict(valid_risk_request_data)
    request_data["buyerDecision"] = "DISPUTE"

    with pytest.raises(ValidationError) as caught:
        RiskAnalysisRequest.model_validate(request_data)

    response = build_agent_error_response(caught.value)

    assert response.error.code is AgentErrorCode.BUYER_NOT_CONFIRMED
    assert response.error.retryable is False


def test_other_validation_error_maps_to_invalid_request(
    valid_risk_request_data: dict[str, Any],
    copy_dict: Any,
) -> None:
    request_data = copy_dict(valid_risk_request_data)
    request_data["riskFactors"] = []

    with pytest.raises(ValidationError) as caught:
        RiskAnalysisRequest.model_validate(request_data)

    response = build_agent_error_response(caught.value)

    assert response.error.code is AgentErrorCode.INVALID_REQUEST
