"""Durable AgentRun dispatchers for local execution and Cloud Tasks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import json

from invoicex_backend.agent_activity import AgentTrigger
from invoicex_backend.config import BackendSettings

TaskHandler = Callable[[str, AgentTrigger], Awaitable[None]]


class InlineAgentTaskDispatcher:
    """Local/test implementation preserving the Cloud Tasks dispatcher contract."""

    def __init__(self, handler: TaskHandler) -> None:
        self._handler = handler

    async def enqueue(self, invoice_id: str, trigger: AgentTrigger) -> None:
        await self._handler(invoice_id, trigger)


class CloudTasksAgentTaskDispatcher:
    """Enqueue an OIDC-authenticated internal Cloud Run request."""

    def __init__(self, settings: BackendSettings) -> None:
        if not all(
            [
                settings.vertex_ai_project_id,
                settings.cloud_tasks_queue,
                settings.cloud_tasks_location,
                settings.cloud_run_task_audience,
                settings.cloud_tasks_service_account_email,
            ]
        ):
            raise ValueError("Cloud Tasks dispatcher configuration is incomplete")
        from google.cloud import tasks_v2

        self._tasks = tasks_v2
        self._client = tasks_v2.CloudTasksClient()
        self._parent = self._client.queue_path(
            settings.vertex_ai_project_id,
            settings.cloud_tasks_location,
            settings.cloud_tasks_queue,
        )
        self._audience = settings.cloud_run_task_audience
        self._service_account_email = settings.cloud_tasks_service_account_email

    async def enqueue(self, invoice_id: str, trigger: AgentTrigger) -> None:
        payload = json.dumps({"invoiceId": invoice_id, "trigger": trigger.value}).encode("utf-8")
        self._client.create_task(
            parent=self._parent,
            task=self._tasks.Task(
                http_request=self._tasks.HttpRequest(
                    http_method=self._tasks.HttpMethod.POST,
                    url=f"{self._audience.rstrip('/')}/internal/agent-tasks",
                    headers={"Content-Type": "application/json"},
                    body=payload,
                    oidc_token=self._tasks.OidcToken(
                        service_account_email=self._service_account_email,
                        audience=self._audience,
                    ),
                )
            ),
        )


def verify_cloud_tasks_oidc(
    authorization: str | None, *, audience: str, expected_email: str
) -> bool:
    """Verify the task token's audience and calling service account.

    Kept separate from FastAPI so it can be tested without an HTTP server.
    """
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        return False
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests

        claims = id_token.verify_oauth2_token(token, requests.Request(), audience=audience)
        return claims.get("email") == expected_email and claims.get("email_verified") is True
    except Exception:
        return False
