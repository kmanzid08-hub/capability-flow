from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.config import Settings
from app.services.ai_fallback import FallbackAI
from app.services.ai_provider_health import (
    ProviderHealthRegistry,
    classify_provider_failure,
    get_provider_health,
    reset_provider_health_for_tests,
)


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@pytest.fixture(autouse=True)
def reset_global_health() -> None:
    reset_provider_health_for_tests()


def test_daily_quota_opens_provider_circuit() -> None:
    now = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    registry = ProviderHealthRegistry(now=lambda: now)

    snapshot = registry.record_failure(
        "gemini",
        ProviderError("GenerateRequestsPerDayPerProjectPerModel quota exhausted", 429),
    )

    assert snapshot.status == "cooldown"
    assert snapshot.reason == "daily_quota"
    assert snapshot.opened_until == now + timedelta(hours=6)
    assert registry.before_call("gemini") is False


def test_retry_hint_controls_rate_limit_cooldown() -> None:
    now = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    registry = ProviderHealthRegistry(now=lambda: now)

    snapshot = registry.record_failure(
        "groq",
        ProviderError("Rate limit reached. Please try again in 17m27.168s.", 429),
    )

    assert snapshot.status == "cooldown"
    assert snapshot.reason == "rate_limit"
    assert snapshot.opened_until is not None
    assert abs((snapshot.opened_until - now).total_seconds() - 1047.168) < 0.01


def test_request_too_large_does_not_open_provider_circuit() -> None:
    registry = ProviderHealthRegistry()

    snapshot = registry.record_failure(
        "groq",
        ProviderError("Request too large for model on tokens per minute", 413),
    )

    assert snapshot.status == "healthy"
    assert snapshot.reason is None
    assert registry.before_call("groq") is True


def test_transient_failures_open_only_after_threshold() -> None:
    registry = ProviderHealthRegistry()

    first = registry.record_failure("openrouter", ProviderError("Bad gateway", 502))
    second = registry.record_failure("openrouter", ProviderError("Bad gateway", 502))
    third = registry.record_failure("openrouter", ProviderError("Bad gateway", 502))

    assert first.status == "degraded"
    assert second.status == "degraded"
    assert third.status == "cooldown"
    assert third.consecutive_failures == 3


def test_success_resets_degraded_provider() -> None:
    registry = ProviderHealthRegistry()
    registry.record_failure("openai", ProviderError("Service unavailable", 503))

    snapshot = registry.record_success("openai")

    assert snapshot.status == "healthy"
    assert snapshot.consecutive_failures == 0
    assert snapshot.reason is None
    assert snapshot.opened_until is None


def test_expired_circuit_allows_only_one_probe() -> None:
    current = [datetime(2026, 9, 28, 12, 0, tzinfo=UTC)]
    registry = ProviderHealthRegistry(now=lambda: current[0])
    registry.record_failure("groq", ProviderError("Rate limit", 429))

    current[0] = current[0] + timedelta(minutes=3)

    assert registry.before_call("groq") is True
    assert registry.snapshot("groq").status == "probing"
    assert registry.before_call("groq") is False

    registry.record_success("groq")
    assert registry.before_call("groq") is True


def test_output_failure_is_request_specific() -> None:
    disposition = classify_provider_failure(
        RuntimeError("provider stopped because the output token limit was reached")
    )

    assert disposition.kind == "output"
    assert disposition.provider_level is False
    assert disposition.cooldown_seconds is None


@pytest.mark.asyncio
async def test_fallback_skips_provider_while_circuit_is_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        groq_api_key="test-groq-key",
        openrouter_api_key="test-openrouter-key",
        openai_api_key=None,
    )
    service = FallbackAI(settings)
    calls: list[str] = []

    get_provider_health().record_failure(
        "groq",
        ProviderError("tokens per day quota exhausted", 429),
    )

    async def should_not_call_groq(**_: Any) -> tuple[dict[str, Any], str]:
        calls.append("groq")
        raise AssertionError("Groq should have been skipped")

    async def succeed_openrouter(**_: Any) -> tuple[dict[str, Any], str]:
        calls.append("openrouter")
        return {"ok": True}, "openrouter:test"

    monkeypatch.setattr(service, "_generate_groq", should_not_call_groq)
    monkeypatch.setattr(service, "_generate_openrouter", succeed_openrouter)

    data, provider = await service.generate_json(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=100,
    )

    assert calls == ["openrouter"]
    assert data == {"ok": True}
    assert provider == "openrouter:test"


@pytest.mark.asyncio
async def test_successful_fallback_closes_probe_circuit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        groq_api_key="test-groq-key",
        openrouter_api_key=None,
        openai_api_key=None,
    )
    service = FallbackAI(settings)
    health = get_provider_health()

    # Force an immediately expired cooldown by patching the global state's clock through
    # a direct success/failure sequence that leaves the provider probeable.
    health.record_failure("groq", ProviderError("rate limit", 429))
    state = health._states["groq"]  # noqa: SLF001 - intentional white-box circuit test
    state.opened_until = datetime.now(UTC) - timedelta(seconds=1)

    async def succeed_groq(**_: Any) -> tuple[dict[str, Any], str]:
        return {"ok": True}, "groq:test"

    monkeypatch.setattr(service, "_generate_groq", succeed_groq)

    data, provider = await service.generate_json(
        system_prompt="system",
        user_prompt="user",
        schema={"type": "object"},
        max_tokens=100,
    )

    snapshot = health.snapshot("groq")
    assert data == {"ok": True}
    assert provider == "groq:test"
    assert snapshot.status == "healthy"
    assert snapshot.consecutive_failures == 0
