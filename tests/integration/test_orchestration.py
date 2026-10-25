import asyncio

from dynamic_agents.core.orchestrator import OrchestrationService
from dynamic_agents.input.envelope import make_envelope
from dynamic_agents.models.gateway import DeterministicGateway


def test_run_creates_snapshot_and_resume(settings, tmp_path) -> None:
    evidence = tmp_path / "request.md"
    evidence.write_text(
        "supplier component change; validation test; thermal risk", encoding="utf-8"
    )
    service = OrchestrationService(settings, gateway=DeterministicGateway())
    run, token = asyncio.run(
        service.run(make_envelope("Replace supplier component", [str(evidence)]))
    )
    assert run.status.value == "completed"
    assert service.get_snapshot(run.snapshot_id) is not None
    assert service.get_team(run.team_id).torn_down_at is not None
    resumed, new_token = asyncio.run(service.resume(token, "Recheck the supplier change"))
    assert resumed.status.value == "completed"
    assert len(resumed.task_results) == len(run.task_results)
    assert new_token
