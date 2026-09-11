from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import Settings
from app.services.ai_fallback import FallbackAI


def test_openai_key_counts_as_configured_fallback() -> None:
    settings = Settings(
        _env_file=None,
        gemini_api_key=None,
        groq_api_key=None,
        openrouter_api_key=None,
        openai_api_key="test-openai-key",
    )

    assert FallbackAI(settings).configured is True


@pytest.mark.asyncio
async def test_free_text_fallbacks_are_tried_before_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        groq_api_key="test-groq-key",
        openrouter_api_key="test-openrouter-key",
        openai_api_key="test-openai-key",
    )
    service = FallbackAI(settings)
    calls: list[str] = []

    async def fail_groq(**_: Any) -> tuple[dict[str, Any], str]:
        calls.append("groq")
        raise RuntimeError("groq unavailable")

    async def fail_openrouter(**_: Any) -> tuple[dict[str, Any], str]:
        calls.append("openrouter")
        raise RuntimeError("openrouter unavailable")

    async def succeed_openai(**_: Any) -> tuple[dict[str, Any], str]:
        calls.append("openai")
        return {"ok": True}, "openai:gpt-5.6-luna"

    monkeypatch.setattr(service, "_generate_groq", fail_groq)
    monkeypatch.setattr(service, "_generate_openrouter", fail_openrouter)
    monkeypatch.setattr(service, "_generate_openai", succeed_openai)

    data, provider = await service.generate_json(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=100,
    )

    assert calls == ["groq", "openrouter", "openai"]
    assert data == {"ok": True}
    assert provider == "openai:gpt-5.6-luna"


@pytest.mark.asyncio
async def test_openai_retries_truncated_json_with_larger_output_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        groq_api_key=None,
        openrouter_api_key=None,
        openai_api_key="test-openai-key",
        openai_model="gpt-5.6-luna",
    )
    service = FallbackAI(settings)
    token_limits: list[int] = []

    class FakeCompletions:
        async def create(self, **kwargs: Any) -> Any:
            token_limits.append(int(kwargs["max_completion_tokens"]))
            if len(token_limits) == 1:
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            finish_reason="length",
                            message=SimpleNamespace(content='{"ok":', refusal=None),
                        )
                    ]
                )
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(content='{"ok": true}', refusal=None),
                    )
                ]
            )

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("app.services.ai_fallback.AsyncOpenAI", FakeClient)

    data, provider = await service._generate_openai(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=2200,
    )

    assert token_limits == [6000, 12000]
    assert data == {"ok": True}
    assert provider == "openai:gpt-5.6-luna"
