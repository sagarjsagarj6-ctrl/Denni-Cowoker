"""Small in-process metrics snapshot."""

from dataclasses import dataclass, field


@dataclass
class Metrics:
    runs: int = 0
    completed: int = 0
    failed: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    _values: dict[str, int] = field(default_factory=dict)

    def observe(self, name: str, amount: int = 1) -> None:
        self._values[name] = self._values.get(name, 0) + amount

    def snapshot(self) -> dict[str, int]:
        return {
            "runs": self.runs,
            "completed": self.completed,
            "failed": self.failed,
            **self._values,
        }
