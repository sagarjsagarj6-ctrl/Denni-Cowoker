"""Resource limit helpers."""

from dataclasses import dataclass


@dataclass(slots=True)
class Counter:
    limit: int
    value: int = 0

    def increment(self, amount: int = 1) -> None:
        if self.value + amount > self.limit:
            raise RuntimeError("resource limit exceeded")
        self.value += amount
