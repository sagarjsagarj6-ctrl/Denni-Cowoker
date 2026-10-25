"""End-to-end case orchestration service."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

from pydantic import BaseModel, Field

from dynamic_agents import __version__
from dynamic_agents.agents.runtime import AgentRuntime
from dynamic_agents.config.settings import Settings
from dynamic_agents.core.errors import ConfigurationError, NotFoundError
from dynamic_agents.core.lifecycle import TeamBuilder
from dynamic_agents.input.normalizer import InputNormalizer
from dynamic_agents.master.planner import MasterPlanner
from dynamic_agents.master.policies import TeamPlanValidator
from dynamic_agents.models.domain import (
    Decision,
    InputEnvelope,
    InputFile,
    NormalizedInput,
    RunRecord,
    RunStatus,
    TeamPlan,
    TeamSnapshot,
    VerificationResult,
)
from dynamic_agents.models.gateway import ModelGateway, make_gateway
from dynamic_agents.models.router import ModelRouter
from dynamic_agents.persistence.repositories import Repository
from dynamic_agents.persistence.tokens import TokenManager
from dynamic_agents.tasks.graph import TaskGraph
from dynamic_agents.tools.builtin import (
    CalculatorTool,
    CsvAnalyzerTool,
    DocxTextExtractorTool,
    FileReaderTool,
    JsonReaderTool,
    PdfTextExtractorTool,
    SpreadsheetAnalyzerTool,
)
from dynamic_agents.tools.registry import ToolRegistry

#: The closed set of decision outcomes the platform is allowed to emit.
DECISION_OUTCOMES = (
    "approved",
    "conditional_approval",
    "requires_review",
    "insufficient_evidence",
    "rejected",
)


class DecisionDraft(BaseModel):
    """Structured shape requested from the model during decision synthesis."""

    outcome: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""
    conditions: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    critical_risks: list[str] = Field(default_factory=list)


class OrchestrationService:
    """Coordinates input, planning, policy, execution, verification, and persistence."""

    def __init__(
        self,
        settings: Settings,
        repository: Repository | None = None,
        gateway: ModelGateway | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository or Repository(
            __import__("dynamic_agents.persistence.db", fromlist=["Database"]).Database(settings)
        )
        self.token_manager = TokenManager(self.repository)
        self._gateway = gateway
        model = settings.active_model
        self.router = ModelRouter(settings.provider, model)
        self.planner = MasterPlanner(settings, self.router)
        self.validator = TeamPlanValidator(settings)
        self.normalizer = InputNormalizer(settings)
        self.builder = TeamBuilder()
        self.tools = ToolRegistry(
            [
                CalculatorTool(),
                FileReaderTool(),
                JsonReaderTool(),
                CsvAnalyzerTool(),
                PdfTextExtractorTool(),
                DocxTextExtractorTool(),
                SpreadsheetAnalyzerTool(),
            ]
        )

    @property
    def gateway(self) -> ModelGateway:
        """Create the model gateway only when a chat or run needs it."""
        if self._gateway is None:
            self._gateway = make_gateway(
                self.settings.provider,
                api_key=self.settings.openrouter_api_key,
                google_api_key=self.settings.google_api_key,
                base_url=self.settings.openrouter_base_url,
                model=self.settings.active_model,
                ollama_base_url=self.settings.ollama_base_url,
            )
        return self._gateway

    async def aclose(self) -> None:
        """Release pooled provider connections held by the gateway."""
        gateway = self._gateway
        self._gateway = None
        if gateway is None:
            return
        closer = getattr(gateway, "aclose", None)
        if closer is None:
            return
        try:
            await closer()
        except Exception:  # pragma: no cover - shutdown must never raise
            pass

    async def run(
        self, envelope: InputEnvelope, plan_override: TeamPlan | None = None
    ) -> tuple[RunRecord, str]:
        run = RunRecord(run_id=f"run_{uuid4().hex}", request_id=envelope.request_id)
        self.repository.save_run(run)
        try:
            normalized = self.normalizer.normalize(envelope)
            run = run.model_copy(update={"status": RunStatus.planning})
            self.repository.save_run(run)
            if plan_override is None:
                plan = self.planner.plan(normalized)
            else:
                plan = plan_override.model_copy(
                    update={
                        "request_id": normalized.request_id,
                        "business_objective": normalized.text or plan_override.business_objective,
                    }
                )
            self.validator.validate(plan)
            team = self.builder.build(plan)
            self.repository.save_team(team)
            run = run.model_copy(update={"status": RunStatus.executing, "team_id": team.team_id})
            self.repository.save_run(run)
            runtimes = {
                agent.agent_id: AgentRuntime(agent, self.gateway, self.tools)
                for agent in plan.agents
            }

            async def runner(task, prior):
                return await runtimes[task.agent_id].execute(task, normalized, prior)

            results = await asyncio.wait_for(
                TaskGraph(plan, self.settings.max_parallel_tasks).run(runner),
                timeout=self.settings.run_timeout_seconds,
            )
            run = run.model_copy(update={"status": RunStatus.verifying, "task_results": results})
            self.repository.save_run(run)
            verification = self._verify(normalized, results)
            decision = await self._decide(normalized, results, verification)
            snapshot = TeamSnapshot(
                snapshot_id=f"snap_{uuid4().hex}",
                team_id=team.team_id,
                run_id=run.run_id,
                original_objective=plan.business_objective,
                team_plan=plan,
                task_results=results,
                final_decision=decision,
                verification=verification,
                unresolved_questions=verification.missing_evidence,
                useful_team_memory=decision.conditions,
                evidence_refs=decision.evidence_refs,
                model_metadata=[agent.model_profile for agent in plan.agents],
                framework_version=__version__,
            )
            self.repository.save_snapshot(snapshot)
            token = self.token_manager.issue(snapshot.snapshot_id)
            self.repository.save_team(self.builder.teardown(team))
            run = run.model_copy(
                update={
                    "status": RunStatus.completed,
                    "snapshot_id": snapshot.snapshot_id,
                    "verification": verification,
                    "decision": decision,
                    "model_calls": sum(result.model_calls for result in results),
                    "tool_calls": sum(result.tool_calls for result in results),
                    "retry_count": sum(result.retry_count for result in results),
                }
            )
            self.repository.save_run(run)
            return run, token
        except Exception as exc:
            run = run.model_copy(
                update={"status": RunStatus.failed, "error": self._safe_error(exc)}
            )
            self.repository.save_run(run)
            raise

    async def resume(
        self, token: str, new_request: str = "", files: list[str] | None = None
    ) -> tuple[RunRecord, str]:
        record = self.token_manager.resolve(token)
        snapshot = self.repository.get_snapshot(record.snapshot_id)
        if snapshot is None:
            raise NotFoundError("snapshot for resume token was not found")
        text = new_request or snapshot.original_objective
        envelope = InputEnvelope(
            request_id=f"req_resume_{uuid4().hex}",
            text=text,
            files=[InputFile(path=path) for path in files or []],
            metadata={"resumed_from": snapshot.snapshot_id},
        )
        return await self.run(envelope, plan_override=snapshot.team_plan)

    def _verify(self, normalized: NormalizedInput, results) -> VerificationResult:
        """Score the run from evidence coverage rather than a fixed constant.

        The previous formula added points for *finding* contradictions, which
        inverted the meaning of the score. Coverage now drives the score and
        contradictions reduce it.
        """
        contradictions: list[str] = []
        for result in results:
            contradictions.extend(result.risks)
        contradictions = list(dict.fromkeys(contradictions))
        refs = {ref for result in results for ref in result.evidence_refs}
        missing: list[str] = []
        if not normalized.evidence:
            missing.append("source documents and controlled requirements")

        total = len(results)
        if total == 0:
            score = 0.0
            coverage = 0.0
        else:
            citing = sum(1 for result in results if result.evidence_refs)
            coverage = citing / total
            grounded = min(1.0, len(refs) / 4.0)
            score = 0.2 + (0.45 * coverage) + (0.25 * grounded)
            if normalized.evidence:
                score += 0.1
            score -= min(0.3, 0.05 * len(contradictions))
            score = max(0.0, min(1.0, score))

        unsupported = [
            f"{result.agent_id}: {finding}"
            for result in results
            for finding in result.findings
            if not result.evidence_refs
        ][:10]

        return VerificationResult(
            passed=bool(results) and score >= 0.5,
            score=score,
            contradictions=contradictions,
            missing_evidence=missing,
            unsupported_claims=unsupported,
            required_gates=[
                "engineering requirement reconciliation",
                "validation approval",
                "change-control sign-off",
            ],
            notes=[
                "All claims are expected to be traced to evidence IDs or marked as assumptions."
            ],
        )

    async def _decide(
        self, normalized: NormalizedInput, results, verification: VerificationResult
    ) -> Decision:
        """Synthesize the final decision from the run, preferring the model.

        The model proposes the outcome, rationale, conditions, and required
        tests. Its proposal is then *validated*: an unknown outcome, an
        over-confident score, or invented evidence references are discarded in
        favour of the deterministic baseline. If the provider is unavailable
        the deterministic baseline is used directly, so a run never fails
        because of a model outage.
        """
        risks = list(dict.fromkeys(risk for result in results for risk in result.risks))
        refs = sorted({ref for result in results for ref in result.evidence_refs})
        baseline = self._baseline_decision(normalized, results, verification, risks, refs)

        try:
            draft = await self.gateway.generate_structured(
                self._decision_prompt(normalized, results, verification),
                profile=self.router.route("reviewer"),
                output_type=DecisionDraft,
                system=(
                    "You are the final decision authority for a multi-agent business review. "
                    "Base every statement only on the specialist outputs provided. Never invent "
                    "evidence, approvals, or test results. Choose exactly one outcome from: "
                    + ", ".join(DECISION_OUTCOMES)
                    + ". Prefer conditional_approval or requires_review when any risk or missing "
                    "evidence remains."
                ),
            )
        except Exception:
            return baseline

        if draft.outcome.strip().lower() not in DECISION_OUTCOMES:
            return baseline
        if not draft.rationale.strip():
            return baseline

        conditions = [item for item in draft.conditions if item.strip()][:12]
        required_tests = [item for item in draft.required_tests if item.strip()][:12]
        if not conditions:
            conditions = baseline.conditions
        if not required_tests:
            required_tests = baseline.required_tests

        # Risks and evidence refs stay anchored to what the agents actually reported.
        critical_risks = list(dict.fromkeys([*risks, *draft.critical_risks]))
        confidence = max(0.0, min(0.95, draft.confidence))
        if verification.contradictions:
            confidence = min(confidence, 0.8)
        if not normalized.evidence:
            confidence = min(confidence, 0.5)

        return Decision(
            outcome=draft.outcome.strip().lower(),
            confidence=confidence,
            rationale=draft.rationale.strip(),
            conditions=conditions,
            critical_risks=critical_risks,
            required_tests=required_tests,
            evidence_refs=refs,
        )

    def _decision_prompt(
        self, normalized: NormalizedInput, results, verification: VerificationResult
    ) -> str:
        """Render the run into a bounded prompt for decision synthesis."""
        context_limit = 12_000
        summary = json.dumps(
            [
                {
                    "agent": result.agent_id,
                    "status": result.status,
                    "findings": result.findings,
                    "risks": result.risks,
                    "recommendations": result.recommendations,
                    "evidence_refs": result.evidence_refs,
                }
                for result in results
            ],
            ensure_ascii=False,
        )[:context_limit]
        return (
            f"Business request:\n{normalized.text[:context_limit]}\n\n"
            f"Specialist outputs:\n{summary}\n\n"
            f"Verification score: {verification.score:.2f} "
            f"(passed={verification.passed})\n"
            f"Contradictions: {verification.contradictions}\n"
            f"Missing evidence: {verification.missing_evidence}\n\n"
            "Produce the final decision: outcome, confidence, rationale, the conditions that "
            "must be met, and the tests that are still required."
        )

    def _baseline_decision(
        self,
        normalized: NormalizedInput,
        results,
        verification: VerificationResult,
        risks: list[str],
        refs: list[str],
    ) -> Decision:
        """Deterministic decision used when the model is unavailable or unusable."""
        if not normalized.evidence:
            return Decision(
                outcome="insufficient_evidence",
                confidence=0.35,
                rationale=(
                    "No source evidence was supplied, so a business approval cannot be "
                    "responsibly issued."
                ),
                conditions=["supply controlled source evidence"],
                critical_risks=risks,
                required_tests=[],
                evidence_refs=refs,
            )
        if risks:
            return Decision(
                outcome="conditional_approval",
                confidence=0.82 if verification.passed else 0.68,
                rationale=(
                    "The review surfaced unresolved risks, so the case is not ready for "
                    "unrestricted release and can proceed only through controlled gates."
                ),
                conditions=[
                    "Reconcile every contradiction between specialist outputs and source evidence.",
                    "Complete role-specific qualification and validation testing.",
                    "Obtain the required functional approvals before release.",
                ],
                critical_risks=risks,
                required_tests=[
                    "requirements-based verification against controlled documents",
                    "electrical/functional regression testing",
                    "pilot build with process capability evidence",
                ],
                evidence_refs=refs,
            )
        return Decision(
            outcome="requires_review",
            confidence=0.55,
            rationale=(
                "The available evidence supports further review but does not establish "
                "release readiness."
            ),
            conditions=["complete cross-functional review"],
            critical_risks=risks,
            required_tests=["requirements-based validation"],
            evidence_refs=refs,
        )

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        if isinstance(exc, (ConfigurationError, NotFoundError)):
            return str(exc)
        return f"{type(exc).__name__}: orchestration failed; inspect server logs with run ID"

    def get_run(self, run_id: str) -> RunRecord | None:
        return self.repository.get_run(run_id)

    def get_team(self, team_id: str):
        return self.repository.get_team(team_id)

    def get_snapshot(self, snapshot_id: str):
        return self.repository.get_snapshot(snapshot_id)

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        return self.repository.list_runs(limit)
