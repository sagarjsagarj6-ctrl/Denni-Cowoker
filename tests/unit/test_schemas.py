from dynamic_agents.models.domain import (
    AgentSpec,
    ModelProfile,
    ResourceLimits,
    Task,
    TeamPlan,
    VerificationPlan,
)


def test_team_plan_serializes_typed_contract() -> None:
    profile = ModelProfile(profile_id="test", provider="test", model="mock")
    agent = AgentSpec(
        agent_id="agent_a",
        role="engineering",
        objective="review",
        model_profile=profile,
        system_instruction="cite evidence",
        resource_limits=ResourceLimits(),
    )
    plan = TeamPlan(
        request_id="req_1",
        business_objective="review",
        agents=[agent],
        tasks=[Task(task_id="task_a", title="A", objective="review", agent_id="agent_a")],
        verification_plan=VerificationPlan(reviewer_agent_id="agent_a"),
    )
    assert plan.model_validate_json(plan.model_dump_json()).request_id == "req_1"
