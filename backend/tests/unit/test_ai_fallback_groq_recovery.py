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
async def test_groq_retries_json_object_after_json_schema_failure(
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
            return SimpleNamespace(data=[SimpleNamespace(id="openai/gpt-oss-20b")])

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "app.services.ai_fallback.AsyncOpenAI",
        lambda **kwargs: _Client(),
    )

    calls: list[tuple[str, int]] = []

    async def _schema_failure(**kwargs: Any) -> dict[str, Any]:
        calls.append(("json_schema", int(kwargs["max_tokens"])))
        raise ValueError("provider did not return a JSON object")

    async def _json_object_success(**kwargs: Any) -> dict[str, Any]:
        calls.append(("json_object", int(kwargs["max_tokens"])))
        return {"roles": []}

    monkeypatch.setattr(ai, "_chat_json", _schema_failure)
    monkeypatch.setattr(ai, "_chat_json_object", _json_object_success)

    data, provider = await ai._generate_groq(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=4000,
        mode="opportunity",
    )

    assert data == {"roles": []}
    assert provider == "groq:openai/gpt-oss-20b"
    assert calls == [("json_schema", 4000), ("json_object", 4000)]


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
