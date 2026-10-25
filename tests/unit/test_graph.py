import asyncio

from dynamic_agents.models.domain import (
    AgentSpec,
    ModelProfile,
    Task,
    TeamPlan,
    VerificationPlan,
)
from dynamic_agents.tasks.graph import TaskGraph


def test_graph_runs_dependency_waves() -> None:
    profile = ModelProfile(profile_id="p", provider="test", model="m")
    agent = AgentSpec(
        agent_id="a",
        role="engineering",
        objective="x",
        model_profile=profile,
        system_instruction="x",
    )
    plan = TeamPlan(
        request_id="r",
        business_objective="x",
        agents=[agent],
        tasks=[
            Task(task_id="one", title="one", objective="one", agent_id="a"),
            Task(task_id="two", title="two", objective="two", agent_id="a"),
            Task(
                task_id="three",
                title="three",
                objective="three",
                agent_id="a",
                depends_on=["one", "two"],
            ),
        ],
        verification_plan=VerificationPlan(reviewer_agent_id="a"),
    )

    async def runner(task, prior):
        from dynamic_agents.models.domain import TaskResult

        return TaskResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            status="succeeded",
            summary=str(len(prior)),
        )

    results = asyncio.run(TaskGraph(plan, 2).run(runner))
    assert [result.task_id for result in results] == ["one", "two", "three"]
    assert results[-1].summary == "2"
