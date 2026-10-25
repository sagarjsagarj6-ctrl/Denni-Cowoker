import httpx
import pytest

from dynamic_agents.core.errors import ModelProviderError
from dynamic_agents.models.domain import ModelProfile
from dynamic_agents.models.gateway import GeminiGateway, OpenRouterGateway, make_gateway


class RateLimitedResponse:
    status_code = 429
    is_error = True

    def json(self):
        return {"error": {"message": "Rate limit exceeded", "code": 429}}


class RateLimitedClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def post(self, *args, **kwargs):
        return RateLimitedResponse()


def test_provider_error_detail_extracts_api_message():
    response = httpx.Response(
        429,
        json={"error": {"message": "Rate limit exceeded", "code": 429}},
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )

    assert OpenRouterGateway._provider_error_detail(response) == "Rate limit exceeded: 429"


def test_make_gateway_builds_gemini_gateway():
    gateway = make_gateway(
        "gemini",
        api_key=None,
        google_api_key="test-google-key",
        base_url="",
        model="gemini-2.5-flash",
    )

    assert isinstance(gateway, GeminiGateway)
    assert gateway._base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert gateway._headers()["Authorization"] == "Bearer test-google-key"


@pytest.mark.asyncio
async def test_openrouter_gateway_turns_429_into_actionable_provider_error(monkeypatch):
    monkeypatch.setattr(
        "dynamic_agents.models.gateway.httpx.AsyncClient",
        lambda **kwargs: RateLimitedClient(),
    )
    gateway = OpenRouterGateway("secret-test-key", "https://openrouter.ai/api/v1")
    profile = ModelProfile(
        profile_id="reasoning",
        provider="openrouter",
        model="google/gemma-4-31b-it:free",
        capabilities=[],
    )

    with pytest.raises(ModelProviderError) as error:
        await gateway.generate("hi", profile=profile)

    assert error.value.status_code == 429
    assert "rate limit reached" in str(error.value).lower()
    assert "check OpenRouter usage" in str(error.value)
    assert "Rate limit exceeded" in str(error.value)
    assert "secret-test-key" not in str(error.value)
