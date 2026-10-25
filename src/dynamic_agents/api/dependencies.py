"""FastAPI dependency wiring."""

from functools import lru_cache

from dynamic_agents.config.settings import Settings, get_settings
from dynamic_agents.core.orchestrator import OrchestrationService

#: Holds the live service instance so shutdown can close it without creating one.
_service_instance: OrchestrationService | None = None


@lru_cache(maxsize=1)
def get_service() -> OrchestrationService:
    global _service_instance
    _service_instance = OrchestrationService(get_settings())
    return _service_instance


def peek_service() -> OrchestrationService | None:
    """Return the cached service without creating one.

    The shutdown hook uses this so stopping the app never spins up a database
    connection that was never needed.
    """
    return _service_instance


def clear_service() -> None:
    """Drop the cached service so the next request rebuilds it from settings."""
    global _service_instance
    _service_instance = None
    get_service.cache_clear()


def settings() -> Settings:
    return get_settings()
