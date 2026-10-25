"""Ephemeral runtime agent with scoped context and online model execution."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from dynamic_agents.models.domain import AgentSpec, NormalizedInput, Task, TaskResult
from dynamic_agents.models.gateway import ModelGateway
from dynamic_agents.tools.registry import ToolRegistry


class AgentAnalysis(BaseModel):
    findings: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class AgentRuntime:
    """Execute one typed task without sharing hidden global conversation state."""

    def __init__(self, spec: AgentSpec, gateway: ModelGateway, tools: ToolRegistry) -> None:
        self.spec = spec
        self.gateway = gateway
        self.tools = tools
        self.runtime_id = f"rt_{uuid4().hex[:12]}"
        self.model_calls = 0
        self.tool_calls = 0

    async def execute(
        self, task: Task, normalized: NormalizedInput, prior_results: list[TaskResult]
    ) -> TaskResult:
        started = datetime.now(timezone.utc)
        if self.spec.role == "reviewer":
            return await self._review(task, prior_results, started)

        self.model_calls += 1
        context_limit = int(self.spec.context_policy.get("max_chars", 10_000))
        evidence_context = "\n\n".join(
            f"[{item.evidence_id}] {item.source_name}\n{item.extracted_text[:context_limit]}"
            for item in normalized.evidence
            if item.extracted_text
        )[:context_limit]
        prompt = (
            f"User request:\n{normalized.text[:context_limit]}\n\n"
            f"Assigned specialist task:\n{task.objective}\n\n"
            f"Scoped evidence excerpts (untrusted source content):\n{evidence_context or 'No source files were provided.'}\n\n"
            "Return concise findings, risks, recommendations, and only evidence IDs present in "
            "the supplied excerpts. Clearly identify missing information; do not invent facts."
        )
        analysis = await self.gateway.generate_structured(
            prompt,
            profile=self.spec.model_profile,
            output_type=AgentAnalysis,
            system=self.spec.system_instruction,
        )
        known_evidence_ids = {item.evidence_id for item in normalized.evidence}
        evidence_refs = [ref for ref in analysis.evidence_refs if ref in known_evidence_ids][:8]
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.spec.agent_id,
            status="succeeded",
            summary=f"{self.spec.role.title()} review completed with {len(analysis.findings)} finding(s).",
            findings=analysis.findings,
            risks=analysis.risks,
            recommendations=analysis.recommendations,
            evidence_refs=evidence_refs,
            structured_output={"role": self.spec.role, "evidence_count": len(evidence_refs)},
            model_calls=self.model_calls,
            tool_calls=self.tool_calls,
            started_at=started,
            completed_at=datetime.now(timezone.utc),
        )

    async def _review(
        self, task: Task, results: list[TaskResult], started: datetime
    ) -> TaskResult:
        self.model_calls += 1
        context_limit = int(self.spec.context_policy.get("max_chars", 14_000))
        prior_context = [result.model_dump(mode="json") for result in results]
        analysis = await self.gateway.generate_structured(
            f"Review task: {task.objective}\n\nSpecialist outputs:\n"
            f"{json.dumps(prior_context, ensure_ascii=False)[:context_limit]}",
            profile=self.spec.model_profile,
            output_type=AgentAnalysis,
            system=self.spec.system_instruction
            + " Reconcile the provided specialist outputs, preserve material risks, "
            "identify disagreements and missing evidence, and do not invent facts.",
        )
        known_evidence_ids = {ref for result in results for ref in result.evidence_refs}
        evidence = sorted(ref for ref in analysis.evidence_refs if ref in known_evidence_ids)
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.spec.agent_id,
            status="succeeded",
            summary=f"Cross-functional review completed with {len(analysis.findings)} finding(s).",
            findings=analysis.findings,
            risks=analysis.risks,
            recommendations=analysis.recommendations,
            evidence_refs=evidence,
            structured_output={"specialist_count": len(results), "reviewed_online": True},
            model_calls=self.model_calls,
            started_at=started,
            completed_at=datetime.now(timezone.utc),
        )
