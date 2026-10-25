"""User-facing command line interface."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from dynamic_agents import __version__
from dynamic_agents.config.settings import get_settings
from dynamic_agents.core.orchestrator import OrchestrationService
from dynamic_agents.input.envelope import make_envelope
from dynamic_agents.knowledge.ingestion import KnowledgeIngestor
from dynamic_agents.persistence.db import Database
from dynamic_agents.persistence.repositories import Repository

app = typer.Typer(
    add_completion=False, no_args_is_help=True, help="Dynamic multi-agent case orchestration"
)
db_app = typer.Typer(add_completion=False, help="Database administration")
app.add_typer(db_app, name="db")
console = Console()


def service() -> OrchestrationService:
    return OrchestrationService(get_settings())


def require_online_provider() -> None:
    """Stop user-facing generation commands when the online key is unavailable."""
    error = get_settings().provider_error()
    if error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print the framework version."""
    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Validate local configuration and database availability."""
    settings = get_settings()
    error = settings.provider_error()
    database = Database(settings)
    database.upgrade()
    rows = {
        "provider": settings.model_provider,
        "provider_ok": error is None,
        "database_ok": database.health(),
        "data_dir": str(settings.ensure_data_dir()),
    }
    if error:
        rows["provider_message"] = error
    console.print_json(json.dumps(rows, default=str))
    if error:
        raise typer.Exit(code=1)


@app.command("run")
def run_case(
    request: str | None = typer.Argument(None),
    file: Path | None = typer.Option(None, "--file", exists=True, readable=True),
    input_dir: Path | None = typer.Option(None, "--input-dir", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run a new case from text, a request file, and/or an input directory."""
    require_online_provider()
    text = request or ""
    if file:
        text = file.read_text(encoding="utf-8")
    files = (
        [str(path) for path in sorted(input_dir.iterdir()) if path.is_file()] if input_dir else []
    )
    if not text and not files:
        raise typer.BadParameter("provide a request, --file, or --input-dir")
    run, token = asyncio.run(service().run(make_envelope(text, files)))
    result = {
        "run_id": run.run_id,
        "team_id": run.team_id,
        "snapshot_id": run.snapshot_id,
        "resume_token": token,
        "status": run.status.value,
        "decision": run.decision.model_dump() if run.decision else None,
    }
    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        console.print(f"[green]Run completed:[/green] {run.run_id}")
        console.print(f"Team: {run.team_id}\nSnapshot: {run.snapshot_id}\nResume token: {token}")
        console.print(f"Decision: {run.decision.outcome if run.decision else 'unavailable'}")


@app.command()
def resume(
    token: str,
    request: str = typer.Option("", "--request"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Resume a case using an opaque server-side token."""
    require_online_provider()
    run, new_token = asyncio.run(service().resume(token, request))
    result = {
        "run_id": run.run_id,
        "snapshot_id": run.snapshot_id,
        "resume_token": new_token,
        "status": run.status.value,
        "decision": run.decision.model_dump() if run.decision else None,
    }
    if json_output:
        console.print_json(json.dumps(result, default=str))
    else:
        console.print(
            f"[green]Resumed run completed:[/green] {run.run_id}\nNew resume token: {new_token}"
        )


@app.command("inspect-run")
def inspect_run(run_id: str, json_output: bool = typer.Option(False, "--json")) -> None:
    """Inspect a persisted run."""
    record = service().get_run(run_id)
    if record is None:
        raise typer.BadParameter("run not found")
    if json_output:
        console.print_json(record.model_dump_json())
    else:
        console.print(record.model_dump_json(indent=2))


@app.command("inspect-team")
def inspect_team(team_id: str) -> None:
    """Inspect a persisted team plan."""
    team = service().get_team(team_id)
    if team is None:
        raise typer.BadParameter("team not found")
    table = Table("Agent", "Role", "Model", "Tools")
    for agent in team.plan.agents:
        table.add_row(
            agent.agent_id,
            agent.role,
            agent.model_profile.model,
            ", ".join(agent.tool_ids) or "none",
        )
    console.print(table)


@app.command()
def ingest(directory: Path, company_id: str | None = None) -> None:
    """Ingest a directory into the local knowledge store."""
    settings = get_settings()
    repository = Repository(Database(settings))
    count = KnowledgeIngestor(settings, repository).ingest(str(directory), company_id)
    console.print(f"Ingested {count} knowledge chunks")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the FastAPI server."""
    uvicorn.run("dynamic_agents.api.app:app", host=host, port=port, reload=True)


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Create or upgrade the local database schema."""
    Database(get_settings()).upgrade()
    console.print("Database schema is up to date")


if __name__ == "__main__":
    app()
