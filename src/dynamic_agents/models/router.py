"""Configurable routing policy for model profiles."""

from dynamic_agents.models.domain import ModelProfile
from dynamic_agents.models.gateway import DEFAULT_OPENROUTER_MODEL, profile_for


class ModelRouter:
    """Choose a model class from an agent role without hard-coding business flow."""

    def __init__(
        self, provider: str = "openrouter", model: str = DEFAULT_OPENROUTER_MODEL
    ) -> None:
        self.provider = provider
        self.model = model

    def route(self, role: str) -> ModelProfile:
        role_lower = role.lower()
        if "review" in role_lower or "master" in role_lower:
            kind = "reviewer"
        elif "visual" in role_lower:
            kind = "vision"
        elif role_lower in {"engineering", "regulatory", "validation"}:
            kind = "reasoning"
        else:
            kind = "efficient"
        return profile_for(kind, provider=self.provider, model=self.model)
