"""Transport-neutral, sanitized error responses for demo and backend boundaries."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, ValidationError

from invoicex_agents.exceptions import (
    AgentConfigurationError,
    AgentInputError,
    GeminiInvocationError,
    GeminiResponseValidationError,
)
from invoicex_agents.models.common import StrictModel


class AgentErrorCode(StrEnum):
    """Stable public codes that do not expose provider or document details."""

    INVALID_DOCUMENT = "INVALID_DOCUMENT"
    INVALID_REQUEST = "INVALID_REQUEST"
    BUYER_NOT_CONFIRMED = "BUYER_NOT_CONFIRMED"
    AGENT_NOT_CONFIGURED = "AGENT_NOT_CONFIGURED"
    AI_TEMPORARILY_UNAVAILABLE = "AI_TEMPORARILY_UNAVAILABLE"
    AI_REQUEST_FAILED = "AI_REQUEST_FAILED"
    AI_RESPONSE_INVALID = "AI_RESPONSE_INVALID"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"


class AgentErrorDetail(StrictModel):
    """One safe error suitable for direct JSON serialization."""

    code: AgentErrorCode
    message: str = Field(min_length=1, max_length=300)
    retryable: bool


class AgentErrorResponse(StrictModel):
    """Public failure envelope shared by CLI demos and future HTTP adapters."""

    schema_version: Literal["agent-error.v1"] = "agent-error.v1"
    status: Literal["FAILED"] = "FAILED"
    error: AgentErrorDetail


def _is_unconfirmed_buyer_error(error: ValidationError) -> bool:
    for item in error.errors(include_url=False, include_context=False, include_input=False):
        location = {str(part) for part in item.get("loc", ())}
        if location & {"buyerDecision", "buyer_decision"}:
            return True
    return False


def build_agent_error_response(error: Exception) -> AgentErrorResponse:
    """Map internal exceptions to a stable response without echoing raw details."""

    if isinstance(error, AgentConfigurationError):
        detail = AgentErrorDetail(
            code=AgentErrorCode.AGENT_NOT_CONFIGURED,
            message="분석 서비스 설정이 완료되지 않았습니다.",
            retryable=False,
        )
    elif isinstance(error, AgentInputError):
        detail = AgentErrorDetail(
            code=AgentErrorCode.INVALID_DOCUMENT,
            message="업로드한 문서 또는 요청값을 확인해 주세요.",
            retryable=False,
        )
    elif isinstance(error, GeminiInvocationError):
        if error.retryable:
            detail = AgentErrorDetail(
                code=AgentErrorCode.AI_TEMPORARILY_UNAVAILABLE,
                message="분석 서비스가 일시적으로 응답하지 않습니다. 잠시 후 다시 시도해 주세요.",
                retryable=True,
            )
        else:
            detail = AgentErrorDetail(
                code=AgentErrorCode.AI_REQUEST_FAILED,
                message="분석 서비스 요청을 완료하지 못했습니다. 설정을 확인해 주세요.",
                retryable=False,
            )
    elif isinstance(error, GeminiResponseValidationError):
        detail = AgentErrorDetail(
            code=AgentErrorCode.AI_RESPONSE_INVALID,
            message="분석 결과를 안전하게 검증하지 못했습니다. 다시 시도해 주세요.",
            retryable=True,
        )
    elif isinstance(error, ValidationError):
        if _is_unconfirmed_buyer_error(error):
            detail = AgentErrorDetail(
                code=AgentErrorCode.BUYER_NOT_CONFIRMED,
                message="Buyer 확인이 완료된 뒤 Risk 분석을 실행해 주세요.",
                retryable=False,
            )
        else:
            detail = AgentErrorDetail(
                code=AgentErrorCode.INVALID_REQUEST,
                message="Risk 분석 요청값을 확인해 주세요.",
                retryable=False,
            )
    else:
        detail = AgentErrorDetail(
            code=AgentErrorCode.ANALYSIS_FAILED,
            message="분석을 완료하지 못했습니다.",
            retryable=False,
        )
    return AgentErrorResponse(error=detail)
