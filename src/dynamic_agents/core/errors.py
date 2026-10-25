"""Stable, user-safe error taxonomy."""


class DynamicAgentsError(Exception):
    """Base application error."""


class ConfigurationError(DynamicAgentsError):
    """Configuration is missing or invalid."""


class ModelProviderError(DynamicAgentsError):
    """A model provider rejected a request or returned an API error."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class PolicyViolation(DynamicAgentsError):
    """A plan, tool, or request violated a deterministic policy."""


class NotFoundError(DynamicAgentsError):
    """Requested durable object does not exist."""


class InputSecurityError(DynamicAgentsError):
    """Untrusted input failed security validation."""


class OrchestrationError(DynamicAgentsError):
    """The task graph could not complete."""
