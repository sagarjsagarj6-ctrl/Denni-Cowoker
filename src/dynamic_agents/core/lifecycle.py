"""Runtime team lifecycle helpers."""

from datetime import datetime, timezone

from dynamic_agents.models.domain import AgentRuntime, AgentRuntimeState, Team, TeamPlan


class TeamBuilder:
    """Compile a validated plan into ephemeral runtime state."""

    def build(self, plan: TeamPlan) -> Team:
        team_id = f"team_{plan.request_id.removeprefix('req_')[:20]}"
        runtimes = [
            AgentRuntime(
                runtime_id=f"rt_{agent.agent_id}",
                agent_id=agent.agent_id,
                state=AgentRuntimeState.ready,
            )
            for agent in plan.agents
        ]
        return Team(team_id=team_id, request_id=plan.request_id, plan=plan, runtimes=runtimes)

    def teardown(self, team: Team) -> Team:
        return team.model_copy(update={"torn_down_at": datetime.now(timezone.utc)})
