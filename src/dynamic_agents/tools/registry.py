"""Tool registry with permission and call-budget enforcement."""

from typing import Any

from dynamic_agents.core.errors import PolicyViolation
from dynamic_agents.models.domain import AgentSpec
from dynamic_agents.tools.base import Tool, ToolAudit, execute_audited


class ToolRegistry:
    """Resolve only explicitly registered tools and audit every invocation."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools = {tool.tool_id: tool for tool in tools or []}
        self.audits: list[ToolAudit] = []
        self._calls: dict[str, int] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> Tool:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise PolicyViolation(f"unknown tool: {tool_id}") from exc

    def execute(self, agent: AgentSpec, tool_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if tool_id not in agent.tool_ids:
            raise PolicyViolation(f"agent {agent.agent_id} is not assigned tool {tool_id}")
        permission = next((item for item in agent.permissions if item.tool_id == tool_id), None)
        if permission is None or not permission.allowed:
            raise PolicyViolation(f"agent {agent.agent_id} is not permitted to use {tool_id}")
        key = f"{agent.agent_id}:{tool_id}"
        if self._calls.get(key, 0) >= permission.max_calls:
            raise PolicyViolation(f"tool call budget exceeded for {key}")
        self._calls[key] = self._calls.get(key, 0) + 1
        result, audit = execute_audited(self.get(tool_id), payload, agent_id=agent.agent_id)
        self.audits.append(audit)
        return result
