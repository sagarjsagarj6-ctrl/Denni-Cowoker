"""Run event definitions used by the scheduler and observability hooks."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RunEvent(BaseModel):
    """A structured event emitted during a run."""

    event_id: str
    run_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
