"""Redacted, durable agent execution records and role-filtered views."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from invoicex_backend.models import ApiModel


class AgentTrigger(StrEnum):
    INVOICE_CREATED = "INVOICE_CREATED"
    BUYER_CONFIRMED = "BUYER_CONFIRMED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    VAULT_DEPOSIT_CONFIRMED = "VAULT_DEPOSIT_CONFIRMED"
    MANDATE_UPDATED = "MANDATE_UPDATED"


class AgentRunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ToolCallStatus(StrEnum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class AgentRun(ApiModel):
    id: str
    invoice_id: str
    trigger: AgentTrigger
    status: AgentRunStatus
    plan_summary: str = Field(max_length=500)
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error_code: str | None = None


class AgentToolCall(ApiModel):
    id: str
    run_id: str
    sequence: int = Field(ge=1)
    tool_name: str
    status: ToolCallStatus
    input_summary: str = Field(max_length=500)
    output_summary: str = Field(max_length=1000)
    error_code: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class AgentHandoff(ApiModel):
    id: str
    run_id: str
    source_agent: str
    target_agent: str
    reason: str = Field(max_length=500)
    status: ToolCallStatus
    created_at: str
    completed_at: str | None = None


class AgentActivityItem(ApiModel):
    id: str
    kind: Literal["RUN", "TOOL", "HANDOFF"]
    status: str
    title: str
    summary: str
    created_at: str
    method_version: str | None = None
    checks: dict[str, bool] | None = None
    transaction_signature: str | None = None
    explorer_url: str | None = None


class AgentActivityTimeline(ApiModel):
    invoice_id: str
    role: Literal["Supplier", "Investor"]
    runs: list[AgentRun]
    timeline: list[AgentActivityItem]
