"""Deterministic async task graph scheduler with bounded parallelism and retries."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from dynamic_agents.core.errors import OrchestrationError
from dynamic_agents.models.domain import Task, TaskResult, TeamPlan

TaskRunner = Callable[[Task, list[TaskResult]], Awaitable[TaskResult]]


class TaskGraph:
    """Execute independent tasks concurrently and dependencies in later waves."""

    def __init__(self, plan: TeamPlan, max_parallelism: int = 8) -> None:
        self.plan = plan
        self.max_parallelism = max_parallelism
        self.tasks = {task.task_id: task for task in plan.tasks}

    async def run(self, runner: TaskRunner) -> list[TaskResult]:
        results: dict[str, TaskResult] = {}
        pending = set(self.tasks)
        semaphore = asyncio.Semaphore(self.max_parallelism)
        while pending:
            ready = [
                self.tasks[task_id]
                for task_id in pending
                if all(dependency in results for dependency in self.tasks[task_id].depends_on)
            ]
            if not ready:
                raise OrchestrationError("no executable task remains; graph may contain a cycle")
            ready.sort(key=lambda task: (-task.priority, task.task_id))

            async def execute(task: Task) -> TaskResult:
                async with semaphore:
                    prior = [results[dependency] for dependency in task.depends_on]
                    last_error: Exception | None = None
                    for attempt in range(task.max_retries + 1):
                        try:
                            result = await asyncio.wait_for(
                                runner(task, prior), timeout=task.timeout_seconds
                            )
                            return result.model_copy(update={"retry_count": attempt})
                        except Exception as exc:
                            last_error = exc
                            if attempt < task.max_retries:
                                await asyncio.sleep(0)
                    return TaskResult(
                        task_id=task.task_id,
                        agent_id=task.agent_id,
                        status="failed",
                        summary="Task failed after bounded retries.",
                        error_class=type(last_error).__name__ if last_error else "UnknownError",
                        retry_count=task.max_retries,
                    )

            wave = await asyncio.gather(*(execute(task) for task in ready))
            for task, result in zip(ready, wave, strict=True):
                results[task.task_id] = result
                pending.remove(task.task_id)
            if any(
                result.status == "failed" and self.tasks[result.task_id].required for result in wave
            ):
                raise OrchestrationError("a required task failed")
        return [results[task.task_id] for task in self.plan.tasks]
