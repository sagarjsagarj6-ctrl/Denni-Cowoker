"""Decision synthesis: model proposal is validated, baseline is the safety net."""

import asyncio

from dynamic_agents.core.orchestrator import OrchestrationService
from dynamic_agents.models.domain import (
    NormalizedInput,
    TaskResult,
    VerificationResult,
)
from dynamic_agents.models.gateway import DeterministicGateway


class StubGateway(DeterministicGateway):
    """Gateway stub returning a fixed structured draft."""

    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__()
        self.payload = payload

    async def generate_structured(self, prompt, *, profile, output_type, system=""):  # noqa: ANN001
        return output_type.model_validate(self.payload)


def _service(settings, gateway) -> OrchestrationService:
    return OrchestrationService(settings, gateway=gateway)


def _results() -> list[TaskResult]:
    return [
        TaskResult(
            task_id="task_quality",
            agent_id="agent_quality",
            status="succeeded",
            summary="quality review",
            risks=["supplier validation incomplete"],
            evidence_refs=["ev_1"],
        )
    ]


def _normalized(with_evidence: bool = True) -> NormalizedInput:
    return NormalizedInput(
        request_id="req_1",
        text="Replace the supplier component",
        evidence=(
            [
                {
                    "evidence_id": "ev_1",
                    "source_name": "req.md",
                    "mime_type": "text/markdown",
                    "checksum_sha256": "abc",
                    "source_location": "req.md",
                    "extracted_text": "supplier change request",
                }
            ]
            if with_evidence
            else []
        ),
    )


def test_model_proposal_is_used_when_valid(settings) -> None:
    gateway = StubGateway(
        {
            "outcome": "requires_review",
            "confidence": 0.7,
            "rationale": "Independent review is still required.",
            "conditions": ["close the validation gap"],
            "required_tests": ["thermal regression"],
        }
    )
    service = _service(settings, gateway)

    decision = asyncio.run(service._decide(_normalized(), _results(), VerificationResult(
        passed=True, score=0.8
    )))

    assert decision.outcome == "requires_review"
    assert decision.rationale == "Independent review is still required."
    assert decision.conditions == ["close the validation gap"]


def test_unknown_outcome_falls_back_to_baseline(settings) -> None:
    gateway = StubGateway({"outcome": "definitely_approved", "rationale": "looks good"})
    service = _service(settings, gateway)

    decision = asyncio.run(service._decide(_normalized(), _results(), VerificationResult(
        passed=True, score=0.8
    )))

    assert decision.outcome in {"conditional_approval", "requires_review"}


def test_evidence_refs_are_never_invented(settings) -> None:
    gateway = StubGateway(
        {
            "outcome": "approved",
            "rationale": "All good.",
            "confidence": 0.99,
            "critical_risks": ["hallucinated risk"],
        }
    )
    service = _service(settings, gateway)

    decision = asyncio.run(service._decide(_normalized(), _results(), VerificationResult(
        passed=True, score=0.9
    )))

    assert decision.evidence_refs == ["ev_1"]
    assert "supplier validation incomplete" in decision.critical_risks


def test_missing_evidence_caps_confidence(settings) -> None:
    gateway = StubGateway(
        {"outcome": "approved", "rationale": "Looks fine.", "confidence": 0.95}
    )
    service = _service(settings, gateway)

    decision = asyncio.run(service._decide(_normalized(with_evidence=False), _results(),
                                           VerificationResult(passed=False, score=0.3)))

    assert decision.confidence <= 0.5
    assert decision.outcome == "approved"


def test_provider_failure_falls_back_to_baseline(settings) -> None:
    class BrokenGateway(DeterministicGateway):
        async def generate_structured(self, prompt, *, profile, output_type, system=""):  # noqa: ANN001
            raise RuntimeError("provider down")

    service = _service(settings, BrokenGateway())

    decision = asyncio.run(service._decide(_normalized(), _results(), VerificationResult(
        passed=True, score=0.8
    )))

    assert decision.outcome in {"conditional_approval", "requires_review"}
    assert decision.rationale
