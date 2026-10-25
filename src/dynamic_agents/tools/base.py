"""Tool protocol and audit records."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Protocol


class Tool(Protocol):
    tool_id: str
    description: str

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(slots=True)
class ToolAudit:
    agent_id: str
    tool_id: str
    input_hash: str
    started_at: float
    ended_at: float
    success: bool
    error_class: str | None = None
    result_metadata: dict[str, Any] | None = None


def payload_hash(payload: dict[str, Any]) -> str:
    import json

    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def execute_audited(
    tool: Tool, payload: dict[str, Any], *, agent_id: str
) -> tuple[dict[str, Any], ToolAudit]:
    started = time.time()
    try:
        result = tool.execute(payload)
        audit = ToolAudit(
            agent_id,
            tool.tool_id,
            payload_hash(payload),
            started,
            time.time(),
            True,
            result_metadata={"keys": list(result)},
        )
        return result, audit
    except Exception as exc:
        audit = ToolAudit(
            agent_id,
            tool.tool_id,
            payload_hash(payload),
            started,
            time.time(),
            False,
            type(exc).__name__,
        )
        raise
