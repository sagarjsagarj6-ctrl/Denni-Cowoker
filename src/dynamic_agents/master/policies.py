"""Deterministic safety and TeamPlan validation."""

from collections import defaultdict, deque
from collections.abc import Mapping

from dynamic_agents.config.settings import Settings
from dynamic_agents.core.errors import PolicyViolation
from dynamic_agents.models.domain import TeamPlan

FORBIDDEN_TOOLS = {"shell", "exec", "powershell", "subprocess", "browser_unrestricted"}


class TeamPlanValidator:
    """Reject unsafe, cyclic, over-budget, or internally inconsistent plans."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate(self, plan: TeamPlan) -> None:
        if len(plan.agents) > self.settings.max_agents_per_run:
            raise PolicyViolation("team exceeds MAX_AGENTS_PER_RUN")
        if len(plan.tasks) > self.settings.max_tasks_per_run:
            raise PolicyViolation("plan exceeds MAX_TASKS_PER_RUN")
        if plan.resource_limits.max_model_calls > self.settings.max_model_calls:
            raise PolicyViolation("plan exceeds MAX_MODEL_CALLS")
        agents = {agent.agent_id for agent in plan.agents}
        tasks = {task.task_id: task for task in plan.tasks}
        if len(agents) != len(plan.agents) or len(tasks) != len(plan.tasks):
            raise PolicyViolation("agent_id and task_id values must be unique")
        if plan.verification_plan.reviewer_agent_id not in agents:
            raise PolicyViolation("verification reviewer is not part of the team")
        for agent in plan.agents:
            if set(agent.tool_ids) & FORBIDDEN_TOOLS:
                raise PolicyViolation(f"agent {agent.agent_id} requests a forbidden tool")
            permission_ids = {permission.tool_id for permission in agent.permissions}
            if not set(agent.tool_ids) <= permission_ids:
                raise PolicyViolation(f"agent {agent.agent_id} has unpermissioned tools")
        for task in plan.tasks:
            if task.agent_id not in agents:
                raise PolicyViolation(f"task {task.task_id} references an unknown agent")
            if any(dep not in tasks for dep in task.depends_on):
                raise PolicyViolation(f"task {task.task_id} has an unknown dependency")
        self._assert_acyclic(tasks)

    @staticmethod
    def _assert_acyclic(tasks: Mapping[str, object]) -> None:
        indegree = {task_id: 0 for task_id in tasks}
        children: dict[str, list[str]] = defaultdict(list)
        for task_id, task in tasks.items():
            for dependency in task.depends_on:  # type: ignore[attr-defined]
                indegree[task_id] += 1
                children[dependency].append(task_id)
        queue = deque(task_id for task_id, count in indegree.items() if count == 0)
        visited = 0
        while queue:
            current = queue.popleft()
            visited += 1
            for child in children[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if visited != len(tasks):
            raise PolicyViolation("task dependency graph contains a cycle")
