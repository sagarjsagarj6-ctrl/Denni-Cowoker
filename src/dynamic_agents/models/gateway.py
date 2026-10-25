"""Provider-independent model gateway with hosted and local provider support."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel

from dynamic_agents.core.errors import ConfigurationError, ModelProviderError
from dynamic_agents.models.domain import ModelProfile

T = TypeVar("T", bound=BaseModel)

#: Default online model. Kept in one place so every call site stays consistent.
DEFAULT_OPENROUTER_MODEL = "google/gemma-4-31b-it:free"

#: Zero-config free router: OpenRouter picks any currently available free model.
FREE_ROUTER_MODEL = "openrouter/free"

#: Default local model for the free, fully offline Ollama provider.
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"

#: Default hosted Google Gemini model.
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

#: OpenRouter allows 20 free-model requests per minute. Pacing slightly below
#: that ceiling keeps the platform's own fan-out from tripping the limiter.
DEFAULT_RATE_LIMIT_RPM = 15

#: Concurrent model calls allowed at once. Keeps a 12-agent run from opening
#: a dozen sockets against a throttled free tier.
DEFAULT_MAX_CONCURRENT_CALLS = 4

#: How long a rate-limited model stays sidelined before it is retried.
MODEL_COOLDOWN_SECONDS = 120.0

RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

_JSON_FENCE = re.compile(r"^```[^\n]*\n?|```\s*$")


class ModelGateway(Protocol):
    """Stable interface used by the planner and runtimes."""

    async def generate(self, prompt: str, *, profile: ModelProfile, system: str = "") -> str: ...

    async def generate_structured(
        self, prompt: str, *, profile: ModelProfile, output_type: type[T], system: str = ""
    ) -> T: ...

    async def embed(self, text: str) -> list[float]: ...


def extract_json_payload(raw: str) -> str:
    """Recover a JSON document from a model response.

    Free-tier models frequently wrap JSON in markdown fences or add a short
    sentence around it. The typed domain boundary must survive that, so the
    payload is located by scanning for a balanced JSON value instead of
    trusting the raw response to be pure JSON.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = _JSON_FENCE.sub("", text).strip()

    try:
        json.loads(text)
        return text
    except ValueError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : index + 1]
                    try:
                        json.loads(candidate)
                    except ValueError:
                        break
                    return candidate
    return text


@dataclass(slots=True)
class DeterministicGateway:
    """No-network gateway intended only for automated tests via dependency injection."""

    model_name: str = "injected-test-model"

    async def generate(self, prompt: str, *, profile: ModelProfile, system: str = "") -> str:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
        return f"Deterministic analysis {digest}: evidence must be checked against the supplied record."

    async def generate_structured(
        self, prompt: str, *, profile: ModelProfile, output_type: type[T], system: str = ""
    ) -> T:
        return output_type.model_validate({})

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [round(byte / 255, 6) for byte in digest[:16]]


class _RateLimiter:
    """Paces outbound model requests.

    Free tiers advertise a per-minute ceiling, but an agent run issues its
    calls in bursts. Spacing the calls out and capping concurrency keeps the
    platform under the ceiling instead of discovering it through 429s.
    """

    def __init__(self, requests_per_minute: int, max_concurrent: int) -> None:
        rpm = max(0, requests_per_minute)
        self._min_interval = 60.0 / rpm if rpm else 0.0
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent))
        self._lock = asyncio.Lock()
        self._next_slot = 0.0

    async def __aenter__(self) -> "_RateLimiter":
        await self._semaphore.acquire()
        if self._min_interval:
            async with self._lock:
                wait = self._next_slot - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                self._next_slot = time.monotonic() + self._min_interval
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self._semaphore.release()


class _ModelCooldowns:
    """Remembers which models are currently throttled."""

    def __init__(self, cooldown: float = MODEL_COOLDOWN_SECONDS) -> None:
        self._cooldown = cooldown
        self._until: dict[str, float] = {}

    def is_cooled(self, model: str) -> bool:
        return self._until.get(model, 0.0) > time.monotonic()

    def cool(self, model: str, seconds: float | None = None) -> None:
        self._until[model] = time.monotonic() + (self._cooldown if seconds is None else seconds)

    def ready(self, models: list[str]) -> list[str]:
        return [model for model in models if not self.is_cooled(model)]


@dataclass(slots=True)
class _ProviderError:
    """Normalized provider failure payload. Never contains request headers."""

    message: str = ""
    code: str = ""
    raw: str = ""
    limit_source: str = ""
    provider_name: str = ""
    remedy_hint: str = ""

    @property
    def detail(self) -> str:
        parts = [part for part in (self.message, self.code) if part]
        summary = ": ".join(parts)
        if self.raw:
            summary = f"{summary} | {self.raw}" if summary else self.raw
        return summary[:600]


class _HTTPGateway:
    """Shared OpenAI-compatible chat gateway.

    A single pooled client is reused across calls so parallel agents reuse TLS
    connections instead of paying a handshake per model call. Transient
    failures are retried with exponential backoff, requests are paced against
    the provider's published ceiling, and a rate-limited model is sidelined
    for a cooldown so later calls skip straight to a working alternative.
    """

    provider_label = "provider"

    #: Wording appended to rate-limit errors so the message stays provider-specific.
    usage_hint = "check provider usage"

    #: Wording appended when the provider does not serve the requested model.
    model_missing_hint = "verify the model id in Setup & API Keys"

    #: Whether a 429 should be retried against the same model.
    retry_on_rate_limit = True

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        timeout: float = 120.0,
        max_attempts: int = 3,
        backoff_base: float = 0.6,
        rate_limit_rpm: int = DEFAULT_RATE_LIMIT_RPM,
        max_concurrent_calls: int = DEFAULT_MAX_CONCURRENT_CALLS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._max_attempts = max(1, max_attempts)
        self._backoff_base = backoff_base
        self._limiter = _RateLimiter(rate_limit_rpm, max_concurrent_calls)
        self._cooldowns = _ModelCooldowns()
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(self._timeout, connect=15.0),
                        limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
                    )
        return self._client

    async def aclose(self) -> None:
        """Release pooled connections."""
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    async def generate(self, prompt: str, *, profile: ModelProfile, system: str = "") -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = await self._post(
            {
                "model": profile.model,
                "messages": messages,
                "temperature": 0,
            }
        )
        content = self._extract_content(body)
        if not isinstance(content, str):
            raise ConfigurationError("Model provider returned a non-textual response")
        return content

    @staticmethod
    def _extract_content(body: dict[str, object]) -> object:
        """Pull the assistant message text out of an OpenAI-compatible payload."""
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ConfigurationError("Model provider returned an unexpected response shape")
        first = choices[0]
        if not isinstance(first, dict):
            raise ConfigurationError("Model provider returned an unexpected response shape")
        message = first.get("message")
        if not isinstance(message, dict):
            raise ConfigurationError("Model provider returned an unexpected response shape")
        return message.get("content")

    def _candidates(self, model: str) -> list[str]:
        """Models to try, in order. Subclasses add fallback options."""
        return [model]

    async def _post(self, payload: dict[str, object]) -> dict[str, object]:
        """Send a chat completion, transparently falling back when throttled."""
        client = await self._get_client()
        url = f"{self._base_url}/chat/completions"
        model = str(payload.get("model") or "")
        candidates = self._candidates(model)
        last_error: Exception | None = None

        for index, candidate in enumerate(candidates):
            body = dict(payload)
            body["model"] = candidate
            try:
                return await self._post_with_retries(client, url, body)
            except ModelProviderError as exc:
                last_error = exc
                if exc.status_code == 429 and index + 1 < len(candidates):
                    # The model is throttled: park it and try the next option.
                    self._cooldowns.cool(candidate)
                    continue
                raise

        if isinstance(last_error, ModelProviderError):
            raise last_error
        raise ModelProviderError(f"{self.provider_label} request failed", status_code=502) from last_error

    async def _post_with_retries(
        self, client: httpx.AsyncClient, url: str, body: dict[str, object]
    ) -> dict[str, object]:
        last_error: Exception | None = None

        for attempt in range(self._max_attempts):
            try:
                async with self._limiter:
                    response = await client.post(url, headers=self._headers(), json=body)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt + 1 >= self._max_attempts:
                    raise ModelProviderError(
                        f"{self.provider_label} request failed: {type(exc).__name__}",
                        status_code=502,
                    ) from exc
                await asyncio.sleep(self._backoff_base * (2**attempt))
                continue

            status = response.status_code
            if 200 <= status < 300:
                try:
                    parsed = response.json()
                except ValueError as exc:
                    raise ModelProviderError(
                        f"{self.provider_label} returned a non-JSON response", status_code=502
                    ) from exc
                if not isinstance(parsed, dict):
                    raise ModelProviderError(
                        f"{self.provider_label} returned an unexpected response shape",
                        status_code=502,
                    )
                return parsed

            provider_error = self._parse_provider_error(response)
            detail = provider_error.detail if provider_error else ""
            if status == 429 and not self.retry_on_rate_limit:
                raise ModelProviderError(
                    self._error_message(status, detail, provider_error),
                    status_code=429,
                )
            if status in RETRYABLE_STATUS and attempt + 1 < self._max_attempts:
                await asyncio.sleep(self._retry_delay(response, attempt))
                continue

            raise ModelProviderError(
                self._error_message(status, detail, provider_error),
                status_code=status if status >= 400 else 502,
            )

        if isinstance(last_error, ModelProviderError):
            raise last_error
        raise ModelProviderError(f"{self.provider_label} request failed", status_code=502) from last_error

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        headers = getattr(response, "headers", None) or {}
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return min(30.0, float(retry_after))
            except ValueError:
                pass
        return self._backoff_base * (2**attempt)

    def _error_message(
        self, status: int, detail: str, provider_error: _ProviderError | None = None
    ) -> str:
        if status == 429:
            message = self._rate_limit_message(provider_error)
        elif status == 404:
            message = (
                f"{self.provider_label} does not know the requested model. "
                f"{self.model_missing_hint}."
            )
        else:
            message = f"{self.provider_label} returned HTTP {status}"
        return f"{message}. Provider detail: {detail}" if detail else message

    def _rate_limit_message(self, provider_error: _ProviderError | None) -> str:
        """Distinguish an upstream host throttle from an account-level quota."""
        source = (provider_error.limit_source if provider_error else "").lower()
        raw = (provider_error.raw if provider_error else "").lower()

        if "upstream" in source or "upstream" in raw or "shared_pool" in source:
            return (
                f"{self.provider_label} model is temporarily rate-limited upstream by its host "
                "provider (shared free pool). This is not an account-quota problem, so waiting a "
                f"little or switching model is the fix: {self.usage_hint}, pick another model in "
                "Setup & API Keys, or run locally with Ollama."
            )
        if provider_error and provider_error.provider_name:
            return (
                f"{self.provider_label} rate limit reached while serving requests from "
                f"{provider_error.provider_name}. The selected model or its provider may be "
                f"throttling requests. Wait and retry, {self.usage_hint}, or choose another model "
                "in Setup & API Keys."
            )
        return (
            f"{self.provider_label} rate limit reached. The selected model or its provider may be "
            "throttling requests, or the account may have reached its free-model request limit. "
            f"Wait and retry, {self.usage_hint}, or choose another model in Setup & API Keys."
        )

    @staticmethod
    def _parse_provider_error(response: httpx.Response) -> _ProviderError | None:
        """Normalize a provider error body without exposing headers or secrets."""
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None

        error = payload.get("error")
        parsed = _ProviderError()
        if isinstance(error, dict):
            message = error.get("message")
            code = error.get("code")
            parsed.message = str(message).strip() if message is not None else ""
            parsed.code = str(code).strip() if code is not None else ""
            metadata = error.get("metadata")
            if isinstance(metadata, dict):
                parsed.raw = str(metadata.get("raw") or "").strip()
                parsed.limit_source = str(metadata.get("limit_source") or "").strip()
                parsed.provider_name = str(metadata.get("provider_name") or "").strip()
                parsed.remedy_hint = str(metadata.get("remedy_hint") or "").strip()
        elif isinstance(error, str):
            parsed.message = error.strip()
        else:
            return None
        return parsed

    @staticmethod
    def _provider_error_detail(response: httpx.Response) -> str:
        """Extract a short provider message without exposing request headers or secrets."""
        parsed = _HTTPGateway._parse_provider_error(response)
        return parsed.detail if parsed else ""

    async def generate_structured(
        self, prompt: str, *, profile: ModelProfile, output_type: type[T], system: str = ""
    ) -> T:
        schema = json.dumps(output_type.model_json_schema(), separators=(",", ":"))
        instruction = (
            "Return a single JSON object that matches this schema. "
            "Output raw JSON only, with no markdown fences and no commentary.\n"
            f"Schema: {schema}\n\n{prompt}"
        )
        raw = await self.generate(instruction, profile=profile, system=system)
        try:
            return output_type.model_validate_json(extract_json_payload(raw))
        except Exception as first_error:
            repaired = await self._repair_structured(
                instruction, raw, output_type, profile=profile, system=system
            )
            if repaired is None:
                raise ConfigurationError(
                    "Model returned invalid structured output"
                ) from first_error
            return repaired

    async def _repair_structured(
        self,
        instruction: str,
        raw: str,
        output_type: type[T],
        *,
        profile: ModelProfile,
        system: str = "",
    ) -> T | None:
        """Ask the model once more to coerce its own answer into valid JSON."""
        try:
            repaired_raw = await self.generate(
                f"{instruction}\n\nYour previous response was:\n{raw[:4000]}\n\n"
                "Rewrite it as valid JSON only.",
                profile=profile,
                system=system,
            )
            return output_type.model_validate_json(extract_json_payload(repaired_raw))
        except Exception:
            return None

    async def embed(self, text: str) -> list[float]:
        return self._hash_embedding(text)

    @staticmethod
    def _hash_embedding(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [round(byte / 255, 6) for byte in digest[:16]]


class OpenRouterGateway(_HTTPGateway):
    """OpenAI-compatible OpenRouter adapter.

    The application never logs the API key. Structured output parsing is done
    locally so provider differences cannot bypass the typed domain boundary.
    A throttled model is skipped for a cooldown and the request continues on a
    fallback model, because free OpenRouter models share a limited host pool.
    """

    provider_label = "OpenRouter"
    usage_hint = "check OpenRouter usage"
    model_missing_hint = "verify the model id in Setup & API Keys, or use 'openrouter/free'"
    retry_on_rate_limit = False

    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        timeout: float = 120.0,
        max_attempts: int = 3,
        backoff_base: float = 0.6,
        fallback_models: tuple[str, ...] = (),
        rate_limit_rpm: int = DEFAULT_RATE_LIMIT_RPM,
        max_concurrent_calls: int = DEFAULT_MAX_CONCURRENT_CALLS,
    ) -> None:
        if not api_key:
            raise ConfigurationError("OpenRouter API key is not configured")
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
            rate_limit_rpm=rate_limit_rpm,
            max_concurrent_calls=max_concurrent_calls,
        )
        self._fallback_models = tuple(model for model in fallback_models if model)

    def _candidates(self, model: str) -> list[str]:
        ordered = [model, *[name for name in self._fallback_models if name != model]]
        ready = self._cooldowns.ready(ordered)
        return ready or ordered


class GeminiGateway(_HTTPGateway):
    """Google Gemini adapter using Google's OpenAI-compatible endpoint."""

    provider_label = "Google Gemini"
    usage_hint = "check your Google AI Studio API usage and model quotas"
    model_missing_hint = "verify the Gemini model id in Setup & API Keys"
    retry_on_rate_limit = False

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 120.0,
        max_attempts: int = 3,
        backoff_base: float = 0.6,
        rate_limit_rpm: int = 10,
        max_concurrent_calls: int = DEFAULT_MAX_CONCURRENT_CALLS,
    ) -> None:
        if not api_key:
            raise ConfigurationError("Google Gemini API key is not configured")
        super().__init__(
            base_url=GEMINI_OPENAI_BASE_URL,
            api_key=api_key,
            timeout=timeout,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
            rate_limit_rpm=rate_limit_rpm,
            max_concurrent_calls=max_concurrent_calls,
        )


class OllamaGateway(_HTTPGateway):
    """Local Ollama adapter for fully free, offline inference.

    Ollama exposes an OpenAI-compatible surface at ``/v1`` and needs no API
    key, which makes it the cheapest way to run this platform. Local serving
    has no published request ceiling, so requests are not paced.
    """

    provider_label = "Ollama"
    usage_hint = "check that the Ollama server is running and the model is loaded"
    model_missing_hint = "run 'ollama pull <model>' in a terminal, then pick that model"

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 300.0,
        max_attempts: int = 3,
        backoff_base: float = 0.6,
        rate_limit_rpm: int = 0,
        max_concurrent_calls: int = DEFAULT_MAX_CONCURRENT_CALLS,
    ) -> None:
        super().__init__(
            base_url=f"{base_url.rstrip('/')}/v1",
            api_key="ollama",
            timeout=timeout,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
            rate_limit_rpm=rate_limit_rpm,
            max_concurrent_calls=max_concurrent_calls,
        )


def make_gateway(
    provider: str,
    *,
    api_key: str | None,
    google_api_key: str | None = None,
    base_url: str,
    model: str | None,
    ollama_base_url: str | None = None,
    fallback_models: tuple[str, ...] = (),
    rate_limit_rpm: int = DEFAULT_RATE_LIMIT_RPM,
    max_concurrent_calls: int = DEFAULT_MAX_CONCURRENT_CALLS,
) -> ModelGateway:
    """Build a gateway from configuration without leaking secrets."""
    name = provider.lower()
    if name == "openrouter":
        if not api_key or not model:
            raise ConfigurationError("OpenRouter requires OPENROUTER_API_KEY and OPENROUTER_MODEL")
        return OpenRouterGateway(
            api_key=api_key,
            base_url=base_url,
            fallback_models=fallback_models,
            rate_limit_rpm=rate_limit_rpm,
            max_concurrent_calls=max_concurrent_calls,
        )
    if name == "gemini":
        if not google_api_key or not model:
            raise ConfigurationError("Google Gemini requires GOOGLE_API_KEY and GOOGLE_MODEL")
        return GeminiGateway(
            api_key=google_api_key,
            max_concurrent_calls=max_concurrent_calls,
        )
    if name == "ollama":
        base = ollama_base_url or "http://localhost:11434"
        return OllamaGateway(
            base_url=base,
            max_concurrent_calls=max_concurrent_calls,
        )
    raise ConfigurationError(
        f"Provider {provider!r} is not available; use 'openrouter', 'gemini', or 'ollama'."
    )


def profile_for(
    name: str,
    *,
    provider: str = "openrouter",
    model: str = DEFAULT_OPENROUTER_MODEL,
) -> ModelProfile:
    """Return a conservative model profile for a routing class."""
    capabilities = ["structured_output"]
    if name in {"reasoning", "reviewer"}:
        capabilities += ["reasoning"]
    if name == "vision":
        capabilities += ["vision"]
    return ModelProfile(
        profile_id=name,
        provider=provider,
        model=model,
        capabilities=capabilities,
        supports_tools=name in {"reasoning", "reviewer"},
        supports_vision=name == "vision",
        cost_class="low" if name == "efficient" else "medium",
        latency_class="fast" if name == "efficient" else "normal",
    )
