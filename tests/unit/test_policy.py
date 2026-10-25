import pytest

from dynamic_agents.core.errors import PolicyViolation
from dynamic_agents.master.planner import MasterPlanner
from dynamic_agents.master.policies import TeamPlanValidator
from dynamic_agents.models.domain import NormalizedInput


def test_planner_creates_dynamic_supplier_team(settings) -> None:
    normalized = NormalizedInput(
        request_id="req_1", text="replace supplier component; assess cost and validation"
    )
    plan = MasterPlanner(settings).plan(normalized)
    TeamPlanValidator(settings).validate(plan)
    roles = {agent.role for agent in plan.agents}
    assert {"engineering", "cost", "validation", "reviewer"} <= roles


def test_validator_rejects_cycles(settings) -> None:
    normalized = NormalizedInput(request_id="req_1", text="review supplier")
    plan = MasterPlanner(settings).plan(normalized)
    plan.tasks[0] = plan.tasks[0].model_copy(update={"depends_on": ["task_review"]})
    with pytest.raises(PolicyViolation):
        TeamPlanValidator(settings).validate(plan)
