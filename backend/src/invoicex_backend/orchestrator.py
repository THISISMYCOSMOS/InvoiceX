"""Vertex Function Calling orchestration with a strict backend tool boundary."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import secrets
from typing import Any, Protocol

from invoicex_backend.agent_activity import (
    AgentRun,
    AgentRunStatus,
    AgentToolCall,
    AgentTrigger,
    ToolCallStatus,
)
from invoicex_backend.config import BackendSettings
from invoicex_backend.repository import RwaRepository

SAFE_TOOLS = frozenset(
    {
        "analyze_documents",
        "evaluate_risk",
        "wait_for_buyer_confirmation",
        "evaluate_mandate",
        "execute_mandated_investment",
        "check_transaction_status",
        "request_manual_review",
    }
)
ALLOWED_TOOLS: dict[AgentTrigger, frozenset[str]] = {
    AgentTrigger.INVOICE_CREATED: frozenset(
        {"analyze_documents", "wait_for_buyer_confirmation", "request_manual_review"}
    ),
    AgentTrigger.BUYER_CONFIRMED: frozenset({"evaluate_risk", "request_manual_review"}),
    AgentTrigger.OFFER_ACCEPTED: frozenset(
        {"evaluate_mandate", "execute_mandated_investment", "request_manual_review"}
    ),
    AgentTrigger.VAULT_DEPOSIT_CONFIRMED: frozenset(
        {"evaluate_mandate", "execute_mandated_investment", "check_transaction_status"}
    ),
    AgentTrigger.MANDATE_UPDATED: frozenset(
        {"evaluate_mandate", "execute_mandated_investment", "check_transaction_status"}
    ),
}


@dataclass(frozen=True, slots=True)
class FunctionCall:
    name: str
    arguments: dict[str, Any]


class FunctionCallingPlanner(Protocol):
    async def choose_tools(
        self, *, context: dict[str, Any], allowed_tools: frozenset[str]
    ) -> list[FunctionCall]: ...


class DeterministicFunctionPlanner:
    """Local/test planner; production uses VertexFunctionPlanner below."""

    async def choose_tools(
        self, *, context: dict[str, Any], allowed_tools: frozenset[str]
    ) -> list[FunctionCall]:
        status = str(context.get("status", ""))
        preferred = {
            "DOCUMENT_ANALYZING": "analyze_documents",
            "DOCUMENT_REVIEW_REQUIRED": "wait_for_buyer_confirmation",
            "RISK_ASSESSING": "evaluate_risk",
            "RWA_ISSUED": "evaluate_mandate",
            "FUNDING": "check_transaction_status",
        }.get(status, "request_manual_review")
        if preferred not in allowed_tools:
            preferred = next(iter(sorted(allowed_tools)))
        return [FunctionCall(preferred, {"invoice_id": context["invoice_id"], "reason_code": "STATE"})]


class VertexFunctionPlanner:
    """Gemini on Vertex AI, authenticated by Cloud Run ADC (no API key)."""

    def __init__(self, settings: BackendSettings) -> None:
        if not settings.vertex_ai_project_id:
            raise ValueError("VERTEX_AI_PROJECT_ID is required for Vertex function calling")
        from google import genai

        self._types = genai.types
        self._client = genai.Client(
            vertexai=True,
            project=settings.vertex_ai_project_id,
            location=settings.vertex_ai_location,
        )
        self._model = settings.gemini_model

    async def choose_tools(
        self, *, context: dict[str, Any], allowed_tools: frozenset[str]
    ) -> list[FunctionCall]:
        declarations = [
            self._types.FunctionDeclaration(
                name=name,
                description="Choose this backend operation only when the invoice state requires it.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "string"},
                        "reason_code": {"type": "string", "maxLength": 64},
                    },
                    "required": ["invoice_id", "reason_code"],
                    "additionalProperties": False,
                },
            )
            for name in sorted(allowed_tools)
        ]
        response = self._client.models.generate_content(
            model=self._model,
            contents=[
                "Select the next safe backend tool. Never invent money, wallets, addresses, "
                "limits, or arguments. Context: " + str(context)
            ],
            config=self._types.GenerateContentConfig(
                temperature=0,
                tools=[self._types.Tool(function_declarations=declarations)],
            ),
        )
        return [
            FunctionCall(name=call.name, arguments=dict(call.args or {}))
            for call in (getattr(response, "function_calls", None) or [])
        ]


ToolExecutor = Callable[[str, str, str], Awaitable[str]]
ContextGetter = Callable[[str], dict[str, Any]]


class VertexOrchestrator:
    """Persists every decision and rejects model input outside its narrow contract."""

    def __init__(
        self,
        *,
        repository: RwaRepository,
        planner: FunctionCallingPlanner,
        context_getter: ContextGetter,
        tool_executor: ToolExecutor,
        max_tool_calls: int = 5,
    ) -> None:
        self._repository = repository
        self._planner = planner
        self._context_getter = context_getter
        self._tool_executor = tool_executor
        self._max_tool_calls = max_tool_calls

    async def run(self, invoice_id: str, trigger: AgentTrigger) -> AgentRun:
        now = datetime.now(UTC).isoformat()
        run = AgentRun(
            id=f"RUN-{secrets.token_urlsafe(12)}",
            invoice_id=invoice_id,
            trigger=trigger,
            status=AgentRunStatus.RUNNING,
            plan_summary="Vertex AI가 안전한 다음 업무 도구를 선택 중입니다.",
            created_at=now,
            started_at=now,
        )
        self._repository.save_agent_run(run)
        allowed = ALLOWED_TOOLS[trigger]
        try:
            calls = await self._planner.choose_tools(
                context=self._context_getter(invoice_id), allowed_tools=allowed
            )
            if len(calls) > self._max_tool_calls:
                raise ValueError("MAX_TOOL_CALLS_EXCEEDED")
            for sequence, call in enumerate(calls, start=1):
                await self._execute_call(run, sequence, call, allowed)
            completed = datetime.now(UTC).isoformat()
            run = run.model_copy(
                update={
                    "status": AgentRunStatus.COMPLETED,
                    "completed_at": completed,
                    "plan_summary": "안전한 Backend 도구 실행을 완료했습니다.",
                }
            )
        except Exception as exc:
            completed = datetime.now(UTC).isoformat()
            run = run.model_copy(
                update={
                    "status": AgentRunStatus.FAILED,
                    "completed_at": completed,
                    "error_code": str(exc)[:64],
                    "plan_summary": "자동 처리가 중단되어 수동 검토가 필요합니다.",
                }
            )
        self._repository.save_agent_run(run)
        return run

    async def _execute_call(
        self, run: AgentRun, sequence: int, call: FunctionCall, allowed: frozenset[str]
    ) -> None:
        now = datetime.now(UTC).isoformat()
        record = AgentToolCall(
            id=f"CALL-{secrets.token_urlsafe(12)}",
            run_id=run.id,
            sequence=sequence,
            tool_name=call.name,
            status=ToolCallStatus.REQUESTED,
            input_summary="redacted invoice_id + reason_code",
            output_summary="",
            started_at=now,
        )
        invalid = (
            call.name not in SAFE_TOOLS
            or call.name not in allowed
            or set(call.arguments) - {"invoice_id", "reason_code"}
            or call.arguments.get("invoice_id") != run.invoice_id
            or not isinstance(call.arguments.get("reason_code"), str)
        )
        if invalid:
            self._repository.save_agent_tool_call(
                record.model_copy(
                    update={
                        "status": ToolCallStatus.REJECTED,
                        "output_summary": "허용되지 않은 도구 또는 인자를 Backend가 거절했습니다.",
                        "error_code": "UNSAFE_FUNCTION_CALL",
                        "completed_at": datetime.now(UTC).isoformat(),
                    }
                )
            )
            raise ValueError("UNSAFE_FUNCTION_CALL")
        try:
            output = await self._tool_executor(run.invoice_id, call.name, call.arguments["reason_code"])
            self._repository.save_agent_tool_call(
                record.model_copy(
                    update={
                        "status": ToolCallStatus.COMPLETED,
                        "output_summary": output[:1000],
                        "completed_at": datetime.now(UTC).isoformat(),
                    }
                )
            )
        except Exception as exc:
            self._repository.save_agent_tool_call(
                record.model_copy(
                    update={
                        "status": ToolCallStatus.FAILED,
                        "output_summary": "Backend 정책 또는 도메인 실행이 실패했습니다.",
                        "error_code": type(exc).__name__,
                        "completed_at": datetime.now(UTC).isoformat(),
                    }
                )
            )
            raise
