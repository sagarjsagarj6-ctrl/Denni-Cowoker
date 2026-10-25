import asyncio

from dynamic_agents.core.orchestrator import OrchestrationService
from dynamic_agents.input.envelope import make_envelope
from dynamic_agents.models.gateway import DeterministicGateway


def test_run_completes_with_injected_test_gateway(settings) -> None:
    service = OrchestrationService(settings, gateway=DeterministicGateway())
    run, token = asyncio.run(
        service.run(make_envelope("Review an operational change and identify its risks."))
    )

    assert run.status == "completed"
    assert run.snapshot_id is not None
    assert token
