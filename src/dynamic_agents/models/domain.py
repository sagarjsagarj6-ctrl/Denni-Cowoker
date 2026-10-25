"""Pydantic domain contracts shared by planning, execution, API, and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RunStatus(StrEnum):
    accepted = "accepted"
    planning = "planning"
    executing = "executing"
    verifying = "verifying"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class InputKind(StrEnum):
    text = "text"
    file = "file"
    image = "image"
    audio = "audio"
    video = "video"


class InputFile(StrictModel):
    path: str
    display_name: str | None = None
    mime_type: str | None = None


class InputEnvelope(StrictModel):
    request_id: str
    text: str = ""
    files: list[InputFile] = Field(default_factory=list)
    company_id: str | None = None
    case_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(StrictModel):
    evidence_id: str
    source_name: str
    mime_type: str
    checksum_sha256: str
    source_location: str
    kind: InputKind = InputKind.file
    extracted_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    reference: str | None = None
    trusted: bool = False


class NormalizedInput(StrictModel):
    request_id: str
    text: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    company_id: str | None = None
    case_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompanyContext(StrictModel):
    company_id: str
    company_name: str | None = None
    product: str | None = None
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    access_scope: str = "default"


class ModelProfile(StrictModel):
    profile_id: str
    provider: str
    model: str
    capabilities: list[str] = Field(default_factory=list)
    context_window: int = Field(default=8192, ge=256)
    supports_tools: bool = False
    supports_vision: bool = False
    cost_class: str = "low"
    latency_class: str = "normal"


class ToolPermission(StrictModel):
    tool_id: str
    allowed: bool = True
    reason: str = ""
    max_calls: int = Field(default=20, ge=0)


class ResourceLimits(StrictModel):
    max_model_calls: int = Field(default=10, ge=0)
    max_tool_calls: int = Field(default=20, ge=0)
    timeout_seconds: int = Field(default=300, ge=1)
    max_output_chars: int = Field(default=12000, ge=100)


class AgentSpec(StrictModel):
    agent_id: str
    role: str
    objective: str
    model_profile: ModelProfile
    system_instruction: str
    context_policy: dict[str, Any] = Field(default_factory=dict)
    tool_ids: list[str] = Field(default_factory=list)
    permissions: list[ToolPermission] = Field(default_factory=list)
    input_requirements: list[str] = Field(default_factory=list)
    output_schema: str = "TaskResult"
    dependencies: list[str] = Field(default_factory=list)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)


class AgentRuntimeState(StrEnum):
    created = "created"
    ready = "ready"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class AgentRuntime(StrictModel):
    runtime_id: str
    agent_id: str
    state: AgentRuntimeState = AgentRuntimeState.created
    current_task_id: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)


class TaskDependency(StrictModel):
    task_id: str
    depends_on: list[str] = Field(default_factory=list)


class Task(StrictModel):
    task_id: str
    title: str
    objective: str
    agent_id: str
    depends_on: list[str] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100)
    timeout_seconds: int = Field(default=300, ge=1)
    max_retries: int = Field(default=1, ge=0, le=5)
    required: bool = True


class TaskResult(StrictModel):
    task_id: str
    agent_id: str
    status: str
    summary: str
    findings: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    structured_output: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime = Field(default_factory=utc_now)
    error_class: str | None = None


class AgentMessage(StrictModel):
    message_id: str
    run_id: str
    sender_agent_id: str
    recipient_agent_id: str | None = None
    message_type: str
    payload: dict[str, Any]
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class VerificationResult(StrictModel):
    passed: bool
    score: float = Field(ge=0, le=1)
    contradictions: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    required_gates: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Decision(StrictModel):
    outcome: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    conditions: list[str] = Field(default_factory=list)
    critical_risks: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class VerificationPlan(StrictModel):
    reviewer_agent_id: str
    checks: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)


class TeamPlan(StrictModel):
    request_id: str
    business_objective: str
    assumptions: list[str] = Field(default_factory=list)
    agents: list[AgentSpec]
    tasks: list[Task]
    dependencies: list[TaskDependency] = Field(default_factory=list)
    shared_context_policy: dict[str, Any] = Field(default_factory=dict)
    verification_plan: VerificationPlan
    expected_deliverables: list[str] = Field(default_factory=list)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)

    @field_validator("agents", "tasks")
    @classmethod
    def non_empty(cls, value: list[Any]) -> list[Any]:
        if not value:
            raise ValueError("must not be empty")
        return value


class Team(StrictModel):
    team_id: str
    request_id: str
    plan: TeamPlan
    runtimes: list[AgentRuntime] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    torn_down_at: datetime | None = None


class TeamSnapshot(StrictModel):
    snapshot_id: str
    team_id: str
    run_id: str
    original_objective: str
    team_plan: TeamPlan
    task_results: list[TaskResult] = Field(default_factory=list)
    final_decision: Decision
    verification: VerificationResult
    unresolved_questions: list[str] = Field(default_factory=list)
    useful_team_memory: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    model_metadata: list[ModelProfile] = Field(default_factory=list)
    framework_version: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ResumeTokenRecord(StrictModel):
    token_id: str
    token_hash: str
    snapshot_id: str
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    revoked: bool = False


class RunRecord(StrictModel):
    run_id: str
    request_id: str
    status: RunStatus = RunStatus.accepted
    team_id: str | None = None
    snapshot_id: str | None = None
    error: str | None = None
    task_results: list[TaskResult] = Field(default_factory=list)
    verification: VerificationResult | None = None
    decision: Decision | None = None
    model_calls: int = 0
    tool_calls: int = 0
    retry_count: int = 0
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class EvaluationRecord(StrictModel):
    evaluation_id: str
    case_id: str
    run_id: str
    passed: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
