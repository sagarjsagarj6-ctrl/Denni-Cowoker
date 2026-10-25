from pathlib import Path

import pytest

from dynamic_agents.config.settings import Settings
from dynamic_agents.persistence.db import Database
from dynamic_agents.persistence.repositories import Repository


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        data_dir=tmp_path / "data",
        model_provider="openrouter",
        openrouter_api_key="test-only-key",
        openrouter_model="test-only-model",
        anthropic_api_key=None,
        openai_api_key=None,
        groq_api_key=None,
        google_api_key=None,
    )


@pytest.fixture
def repository(settings: Settings) -> Repository:
    return Repository(Database(settings))
