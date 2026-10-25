"""Typed environment-driven settings and provider validation."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dynamic_agents.models.gateway import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENROUTER_MODEL,
)

#: Providers this build can talk to.
SUPPORTED_PROVIDERS = ("openrouter", "gemini", "ollama")


class Settings(BaseSettings):
    """Application configuration with safe local defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    database_url: str = Field(
        default="sqlite:///./.data/dynamic_agents.db", validation_alias="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    model_provider: str = Field(default="openrouter", validation_alias="MODEL_PROVIDER")
    openrouter_api_key: str | None = Field(default=None, validation_alias="OPENROUTER_API_KEY")
    openrouter_model: str | None = Field(default=None, validation_alias="OPENROUTER_MODEL")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", validation_alias="OPENROUTER_BASE_URL"
    )
    google_model: str | None = Field(default=None, validation_alias="GOOGLE_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    ollama_model: str | None = Field(default=None, validation_alias="OLLAMA_MODEL")
    google_api_key: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    max_agents_per_run: int = Field(default=12, ge=1, le=100, validation_alias="MAX_AGENTS_PER_RUN")
    max_tasks_per_run: int = Field(default=32, ge=1, le=500, validation_alias="MAX_TASKS_PER_RUN")
    max_parallel_tasks: int = Field(default=8, ge=1, le=100, validation_alias="MAX_PARALLEL_TASKS")
    max_model_calls: int = Field(default=100, ge=1, le=10000, validation_alias="MAX_MODEL_CALLS")
    max_tool_calls_per_agent: int = Field(
        default=20, ge=0, le=1000, validation_alias="MAX_TOOL_CALLS_PER_AGENT"
    )
    run_timeout_seconds: int = Field(
        default=1800, ge=1, le=86400, validation_alias="RUN_TIMEOUT_SECONDS"
    )
    max_file_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        le=1024 * 1024 * 1024,
        validation_alias="MAX_FILE_SIZE_BYTES",
    )
    knowledge_top_k: int = Field(default=8, ge=1, le=100, validation_alias="KNOWLEDGE_TOP_K")
    allowed_http_domains: str = Field(default="", validation_alias="ALLOWED_HTTP_DOMAINS")
    data_dir: Path = Field(default=Path(".data"), validation_alias="DATA_DIR")
    log_json: bool = Field(default=False, validation_alias="LOG_JSON")

    @property
    def allowed_domains(self) -> set[str]:
        return {
            value.strip().lower() for value in self.allowed_http_domains.split(",") if value.strip()
        }

    @property
    def provider(self) -> str:
        """Return the normalized provider name."""
        return self.model_provider.strip().lower()

    @property
    def active_model(self) -> str:
        """Return the model id that the current provider should use."""
        if self.provider == "ollama":
            return self.ollama_model or DEFAULT_OLLAMA_MODEL
        if self.provider == "gemini":
            return self.google_model or DEFAULT_GEMINI_MODEL
        return self.openrouter_model or DEFAULT_OPENROUTER_MODEL

    def provider_error(self) -> str | None:
        """Return an actionable provider configuration error, if any."""
        provider = self.provider
        if provider == "openrouter":
            if not self.openrouter_api_key:
                return "OPENROUTER_API_KEY is missing; add your API key in Setup & API Keys."
            if not self.openrouter_model:
                return "OPENROUTER_MODEL is missing; set a currently available model in .env."
            return None
        if provider == "ollama":
            if not self.ollama_base_url:
                return "OLLAMA_BASE_URL is missing; point it at your local Ollama server."
            return None
        if provider == "gemini":
            if not self.google_api_key:
                return "GOOGLE_API_KEY is missing; add your Gemini API key in Setup & API Keys."
            if not self.active_model:
                return "GOOGLE_MODEL is missing; set a Gemini model in .env."
            return None
        return (
            f"Unsupported MODEL_PROVIDER={self.model_provider!r}; "
            f"use one of: {', '.join(SUPPORTED_PROVIDERS)}."
        )

    def ensure_data_dir(self) -> Path:
        """Create and return the application data directory."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    def database_path(self) -> Path:
        """Resolve a SQLite URL to a local path."""
        if self.database_url.startswith("sqlite:///"):
            raw = self.database_url.removeprefix("sqlite:///")
            path = Path(raw)
            return path if path.is_absolute() else Path.cwd() / path
        return self.ensure_data_dir() / "dynamic_agents.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process settings singleton."""
    return Settings()
