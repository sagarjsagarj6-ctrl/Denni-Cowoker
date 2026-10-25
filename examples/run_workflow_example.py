"""Run and resume a simple request with the local deterministic provider."""

import asyncio
from pathlib import Path

from rich.console import Console

from dynamic_agents.config.settings import Settings
from dynamic_agents.core.orchestrator import OrchestrationService
from dynamic_agents.input.envelope import make_envelope

console = Console()


async def main() -> None:
    settings = Settings(
        model_provider="test",
        database_url="sqlite:///./.data/dynamic_agents.db",
        data_dir=Path(".data"),
    )
    service = OrchestrationService(settings)
    request = "Review an operational change and identify risks and required validation."

    run, token = await service.run(make_envelope(request))
    console.print(f"Run status: {run.status.value}")
    console.print(f"Decision: {run.decision.outcome if run.decision else 'unavailable'}")
    console.print(f"Resume token: {token}")

    resumed, _new_token = await service.resume(
        token=token,
        new_request="Summarize the remaining validation steps.",
    )
    console.print(f"Resumed run status: {resumed.status.value}")


if __name__ == "__main__":
    asyncio.run(main())
