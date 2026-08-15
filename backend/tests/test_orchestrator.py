import asyncio
from pathlib import Path

from invoicex_backend.agent_activity import AgentTrigger, ToolCallStatus
from invoicex_backend.orchestrator import FunctionCall, VertexOrchestrator
from invoicex_backend.repository import SQLiteRwaRepository


class _Planner:
    def __init__(self, calls: list[FunctionCall]) -> None:
        self.calls = calls

    async def choose_tools(self, **_: object) -> list[FunctionCall]:
        return self.calls


def test_orchestrator_rejects_money_and_wallet_arguments(tmp_path: Path) -> None:
    repository = SQLiteRwaRepository(tmp_path / "activity.sqlite3")

    async def executor(*_: str) -> str:
        raise AssertionError("unsafe call must not execute")

    orchestrator = VertexOrchestrator(
        repository=repository,
        planner=_Planner(
            [
                FunctionCall(
                    "evaluate_risk",
                    {"invoice_id": "INV-1", "reason_code": "STATE", "amount": 100},
                )
            ]
        ),
        context_getter=lambda invoice_id: {"invoice_id": invoice_id, "status": "RISK_ASSESSING"},
        tool_executor=executor,
    )
    run = asyncio.run(orchestrator.run("INV-1", AgentTrigger.BUYER_CONFIRMED))
    calls = repository.list_agent_tool_calls(run.id)
    repository.close()

    assert run.status == "FAILED"
    assert calls[0].status == ToolCallStatus.REJECTED
    assert calls[0].error_code == "UNSAFE_FUNCTION_CALL"
