"""Explicitly unavailable shell sandbox boundary for the default runtime."""

from dynamic_agents.core.errors import PolicyViolation


def reject_code_execution() -> None:
    """Reject code execution until a separately audited sandbox is configured."""
    raise PolicyViolation("arbitrary code execution is disabled in the default runtime")
