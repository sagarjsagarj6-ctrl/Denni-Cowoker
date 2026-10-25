from fastapi.testclient import TestClient

import dynamic_agents.api.app as api_module
from dynamic_agents.api.app import create_app
from dynamic_agents.api.dependencies import get_service
from dynamic_agents.api.dependencies import settings as settings_dependency
from dynamic_agents.core.errors import ModelProviderError
from dynamic_agents.core.orchestrator import OrchestrationService
from dynamic_agents.master.conversation import ConversationReply
from dynamic_agents.models.gateway import DeterministicGateway


class ConversationGateway(DeterministicGateway):
    async def generate_structured(self, prompt, *, profile, output_type, system=""):
        return ConversationReply(
            action="reply",
            message="Hi! What change would you like the team to review?",
        )


class RateLimitedGateway(DeterministicGateway):
    async def generate_structured(self, prompt, *, profile, output_type, system=""):
        raise ModelProviderError(
            "OpenRouter rate limit reached. Check OpenRouter usage.", status_code=429
        )


def test_api_run_and_resume(settings) -> None:
    service = OrchestrationService(settings, gateway=DeterministicGateway())
    app = create_app()
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[settings_dependency] = lambda: settings
    client = TestClient(app)
    response = client.post("/v1/runs", json={"text": "Review a supplier component change."})
    assert response.status_code == 200
    body = response.json()
    resumed = client.post(
        f"/v1/runs/{body['run']['run_id']}/resume",
        json={"resume_token": body["resume_token"], "new_request": "Recheck the decision."},
    )
    assert resumed.status_code == 200
    assert resumed.json()["run"]["status"] == "completed"


def test_conversation_endpoint_returns_assistant_reply(settings) -> None:
    service = OrchestrationService(settings, gateway=ConversationGateway())
    app = create_app()
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[settings_dependency] = lambda: settings
    client = TestClient(app)

    response = client.post(
        "/v1/conversation/respond",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "reply"
    assert response.json()["message"].startswith("Hi!")


def test_conversation_endpoint_preserves_provider_rate_limit(settings) -> None:
    service = OrchestrationService(settings, gateway=RateLimitedGateway())
    app = create_app()
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[settings_dependency] = lambda: settings
    client = TestClient(app)

    response = client.post(
        "/v1/conversation/respond",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 429
    assert "rate limit reached" in response.json()["detail"].lower()


def test_test_provider_connection_is_rejected(monkeypatch, settings) -> None:
    monkeypatch.setattr(
        api_module,
        "get_settings",
        lambda: settings.model_copy(update={"model_provider": "test"}),
    )
    client = TestClient(create_app())

    response = client.post("/v1/config/test", json={"model_provider": "test"})

    assert response.status_code == 422


def test_config_rejects_unsupported_provider() -> None:
    client = TestClient(create_app())

    response = client.post("/v1/config", json={"model_provider": "openai"})

    assert response.status_code == 422


def test_gemini_config_returns_only_masked_api_key(settings) -> None:
    gemini_settings = settings.model_copy(
        update={
            "model_provider": "gemini",
            "google_api_key": "google-test-key",
            "google_model": "gemini-2.5-flash",
        }
    )
    app = create_app()
    app.dependency_overrides[settings_dependency] = lambda: gemini_settings

    response = TestClient(app).get("/v1/config")

    assert response.status_code == 200
    assert response.json()["google_api_key_masked"] == "google-...-key"
    assert "google-test-key" not in response.text


def test_gemini_connection_test_requires_api_key(monkeypatch, settings) -> None:
    monkeypatch.setattr(
        api_module,
        "get_settings",
        lambda: settings.model_copy(update={"google_api_key": None}),
    )
    response = TestClient(create_app()).post(
        "/v1/config/test", json={"model_provider": "gemini"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Google Gemini API key" in response.json()["message"]


def test_upload_rejects_file_over_configured_limit(monkeypatch, settings, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        api_module,
        "get_settings",
        lambda: settings.model_copy(update={"max_file_size_bytes": 1024}),
    )
    client = TestClient(create_app())

    response = client.post(
        "/v1/upload",
        files={"file": ("large.txt", b"x" * 1025, "text/plain")},
    )

    assert response.status_code == 413
