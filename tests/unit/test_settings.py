from dynamic_agents.config.settings import Settings


def test_configured_online_provider_is_valid(settings: Settings) -> None:
    assert settings.provider_error() is None


def test_openrouter_requires_both_credentials() -> None:
    settings = Settings(model_provider="openrouter", openrouter_api_key=None, openrouter_model=None)
    assert "OPENROUTER_API_KEY" in (settings.provider_error() or "")


def test_gemini_requires_api_key() -> None:
    settings = Settings(model_provider="gemini", google_api_key=None)
    assert "GOOGLE_API_KEY" in (settings.provider_error() or "")


def test_gemini_uses_default_model() -> None:
    settings = Settings(model_provider="gemini", google_api_key="test-key", google_model=None)
    assert settings.active_model == "gemini-2.5-flash"
    assert settings.provider_error() is None


def test_non_online_provider_is_rejected() -> None:
    settings = Settings(model_provider="test")
    assert "Unsupported MODEL_PROVIDER" in (settings.provider_error() or "")


def test_allowed_domains_are_normalized() -> None:
    settings = Settings(allowed_http_domains="Example.com, api.example.com ")
    assert settings.allowed_domains == {"example.com", "api.example.com"}
