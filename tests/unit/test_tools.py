import pytest

from dynamic_agents.core.errors import PolicyViolation
from dynamic_agents.models.domain import AgentSpec, ModelProfile, ToolPermission
from dynamic_agents.tools.builtin import CalculatorTool, FileReaderTool
from dynamic_agents.tools.registry import ToolRegistry


def test_calculator_is_bounded() -> None:
    assert CalculatorTool().execute({"expression": "2 + 3 * 4"})["value"] == 14
    with pytest.raises(ValueError):
        CalculatorTool().execute({"expression": "__import__('os').getcwd()"})


def test_registry_enforces_scoped_permissions(tmp_path) -> None:
    registry = ToolRegistry([FileReaderTool()])
    agent = AgentSpec(
        agent_id="a",
        role="engineering",
        objective="read",
        model_profile=ModelProfile(profile_id="p", provider="test", model="m"),
        system_instruction="read",
        tool_ids=["file_reader"],
        permissions=[ToolPermission(tool_id="file_reader", max_calls=1)],
    )
    path = tmp_path / "a.txt"
    path.write_text("ok", encoding="utf-8")
    assert (
        registry.execute(agent, "file_reader", {"path": str(path), "root": str(tmp_path)})["text"]
        == "ok"
    )
    with pytest.raises(PolicyViolation):
        registry.execute(agent, "file_reader", {"path": str(path), "root": str(tmp_path)})
