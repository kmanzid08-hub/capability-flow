from types import SimpleNamespace
from typing import Any

import pytest

from app.services.ai_fallback import FallbackAI


class _HealthyProviderState:
    def before_call(self, provider: str) -> bool:
        return True

    def record_success(self, provider: str) -> None:
        return None

    def record_failure(self, provider: str, exc: Exception) -> Any:
        return SimpleNamespace(status="closed", reason=None)

    def snapshot(self, provider: str) -> Any:
        return SimpleNamespace(status="closed", reason=None, opened_until=None)


@pytest.mark.asyncio
async def test_groq_opportunity_prefers_120b_and_skips_json_object_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai = object.__new__(FallbackAI)
    ai.settings = SimpleNamespace(
        groq_api_key="test-key",
        groq_model="openai/gpt-oss-20b",
    )
    ai.provider_health = _HealthyProviderState()

    class _Models:
        async def list(self) -> Any:
            return SimpleNamespace(
                data=[
                    SimpleNamespace(id="openai/gpt-oss-20b"),
                    SimpleNamespace(id="openai/gpt-oss-120b"),
                    SimpleNamespace(id="llama-3.1-8b-instant"),
                ]
            )

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "app.services.ai_fallback.AsyncOpenAI",
        lambda **kwargs: _Client(),
    )

    calls: list[tuple[str, str, int]] = []

    async def _schema(**kwargs: Any) -> dict[str, Any]:
        model = str(kwargs["model"])
        calls.append(("json_schema", model, int(kwargs["max_tokens"])))
        if model == "openai/gpt-oss-120b":
            raise ValueError("provider did not return a JSON object")
        return {"roles": []}

    async def _json_object_should_not_run(**kwargs: Any) -> dict[str, Any]:
        raise AssertionError("opportunity extraction must not use Groq JSON-object retry")

    monkeypatch.setattr(ai, "_chat_json", _schema)
    monkeypatch.setattr(ai, "_chat_json_object", _json_object_should_not_run)

    data, provider = await ai._generate_groq(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=4000,
        mode="opportunity",
    )

    assert data == {"roles": []}
    assert provider == "groq:llama-3.1-8b-instant"
    assert calls == [
        ("json_schema", "openai/gpt-oss-120b", 4000),
        ("json_schema", "llama-3.1-8b-instant", 4000),
    ]


@pytest.mark.asyncio
async def test_opportunity_fallback_uses_provider_safe_groq_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai = object.__new__(FallbackAI)
    ai.settings = SimpleNamespace(
        groq_api_key="test-key",
        openrouter_api_key=None,
        openai_api_key=None,
    )
    ai.provider_health = _HealthyProviderState()

    captured: list[int] = []

    async def _fake_generate_groq(**kwargs: Any) -> tuple[dict[str, Any], str]:
        captured.append(int(kwargs["max_tokens"]))
        return {"roles": []}, "groq:test"

    monkeypatch.setattr(ai, "_generate_groq", _fake_generate_groq)

    await ai.generate_json(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=8192,
        mode="opportunity",
    )

    assert captured == [4000]


@pytest.mark.asyncio
async def test_profile_fallback_keeps_compact_output_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai = object.__new__(FallbackAI)
    ai.settings = SimpleNamespace(
        groq_api_key="test-key",
        openrouter_api_key=None,
        openai_api_key=None,
    )
    ai.provider_health = _HealthyProviderState()

    captured: list[int] = []

    async def _fake_generate_groq(**kwargs: Any) -> tuple[dict[str, Any], str]:
        captured.append(int(kwargs["max_tokens"]))
        return {
            "evidence": [
                {"category": "experience", "title": "Example"},
            ]
        }, "groq:test"

    monkeypatch.setattr(ai, "_generate_groq", _fake_generate_groq)

    await ai.generate_json(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=8192,
        mode="profile",
    )

    assert captured == [3500]


@pytest.mark.asyncio
async def test_opportunity_fallback_preserves_openrouter_budget_after_groq_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai = object.__new__(FallbackAI)
    ai.settings = SimpleNamespace(
        groq_api_key="test-key",
        openrouter_api_key="test-openrouter-key",
        openai_api_key=None,
    )
    ai.provider_health = _HealthyProviderState()

    captured: list[tuple[str, int]] = []

    async def _fake_generate_groq(**kwargs: Any) -> tuple[dict[str, Any], str]:
        captured.append(("groq", int(kwargs["max_tokens"])))
        raise ValueError("groq failed")

    async def _fake_generate_openrouter(**kwargs: Any) -> tuple[dict[str, Any], str]:
        captured.append(("openrouter", int(kwargs["max_tokens"])))
        return {"roles": []}, "openrouter:test"

    monkeypatch.setattr(ai, "_generate_groq", _fake_generate_groq)
    monkeypatch.setattr(ai, "_generate_openrouter", _fake_generate_openrouter)

    data, provider = await ai.generate_json(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=8192,
        mode="opportunity",
    )

    assert data == {"roles": []}
    assert provider == "openrouter:test"
    assert captured == [("groq", 4000), ("openrouter", 8192)]


class _GroqBadRequest(Exception):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__("json_validate_failed")
        self.body = payload
        self.status_code = 400


@pytest.mark.asyncio
async def test_groq_recovers_valid_failed_generation_without_second_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai = object.__new__(FallbackAI)
    ai.settings = SimpleNamespace(
        groq_api_key="test-key",
        groq_model="openai/gpt-oss-20b",
    )
    ai.provider_health = _HealthyProviderState()

    class _Models:
        async def list(self) -> Any:
            return SimpleNamespace(data=[SimpleNamespace(id="openai/gpt-oss-120b")])

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "app.services.ai_fallback.AsyncOpenAI",
        lambda **kwargs: _Client(),
    )

    async def _schema_failure(**kwargs: Any) -> dict[str, Any]:
        raise _GroqBadRequest(
            {
                "error": {
                    "code": "json_validate_failed",
                    "failed_generation": '{"roles":[{"title":"Team Leader"}]}',
                }
            }
        )

    async def _json_object_should_not_run(**kwargs: Any) -> dict[str, Any]:
        raise AssertionError("failed_generation recovery should avoid a second provider call")

    monkeypatch.setattr(ai, "_chat_json", _schema_failure)
    monkeypatch.setattr(ai, "_chat_json_object", _json_object_should_not_run)

    data, provider = await ai._generate_groq(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=4000,
        mode="opportunity",
    )

    assert data == {"roles": [{"title": "Team Leader"}]}
    assert provider == "groq:openai/gpt-oss-120b:recovered"


def test_failed_generation_recovery_rejects_malformed_json() -> None:
    exc = _GroqBadRequest(
        {
            "error": {
                "code": "json_validate_failed",
                "failed_generation": '{"roles":[',
            }
        }
    )
    assert FallbackAI._recover_failed_generation_json(exc) is None
