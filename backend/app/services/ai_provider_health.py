from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Literal

ProviderName = Literal["gemini", "groq", "openrouter", "openai"]
ProviderStatus = Literal["healthy", "degraded", "cooldown", "probing"]
FailureKind = Literal[
    "daily_quota",
    "rate_limit",
    "auth",
    "transient",
    "request_specific",
    "output",
    "unknown",
]

_DEFAULT_RATE_LIMIT_COOLDOWN = 120.0
_DEFAULT_DAILY_QUOTA_COOLDOWN = 21_600.0
_DEFAULT_AUTH_COOLDOWN = 1_800.0
_DEFAULT_TRANSIENT_COOLDOWN = 120.0
_DEFAULT_TRANSIENT_FAILURE_THRESHOLD = 3
_MAX_COOLDOWN_SECONDS = 86_400.0


@dataclass(frozen=True)
class ProviderHealthSnapshot:
    provider: ProviderName
    status: ProviderStatus
    consecutive_failures: int
    opened_until: datetime | None
    reason: FailureKind | None
    last_error_type: str | None
    last_failure_at: datetime | None


@dataclass
class _ProviderState:
    status: ProviderStatus = "healthy"
    consecutive_failures: int = 0
    opened_until: datetime | None = None
    reason: FailureKind | None = None
    last_error_type: str | None = None
    last_failure_at: datetime | None = None
    probe_in_flight: bool = False


@dataclass(frozen=True)
class FailureDisposition:
    kind: FailureKind
    provider_level: bool
    cooldown_seconds: float | None


class ProviderHealthRegistry:
    """Process-wide provider health and circuit-breaker state.

    The current Capability Flow worker runs inside the API process, so a shared in-process
    registry prevents repeated quota/rate-limit calls across jobs and service instances.
    The API surface is intentionally small so this can later be backed by PostgreSQL or
    Redis without changing the callers.
    """

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._lock = RLock()
        self._states: dict[ProviderName, _ProviderState] = {}

    def before_call(self, provider: ProviderName) -> bool:
        """Return True when a provider call may proceed.

        When a cooldown expires, exactly one caller becomes the half-open probe. Other
        concurrent callers continue down the fallback chain until the probe succeeds or
        fails.
        """
        now = self._now()
        with self._lock:
            state = self._states.setdefault(provider, _ProviderState())

            # A half-open probe is already using this provider. Every other caller must
            # continue down the fallback chain until that probe records success/failure.
            if state.probe_in_flight or state.status == "probing":
                return False

            if state.status != "cooldown":
                return True

            if state.opened_until is not None and now < state.opened_until:
                return False

            state.status = "probing"
            state.probe_in_flight = True
            return True

    def record_success(self, provider: ProviderName) -> ProviderHealthSnapshot:
        with self._lock:
            state = self._states.setdefault(provider, _ProviderState())
            state.status = "healthy"
            state.consecutive_failures = 0
            state.opened_until = None
            state.reason = None
            state.last_error_type = None
            state.last_failure_at = None
            state.probe_in_flight = False
            return self._snapshot_locked(provider, state)

    def record_failure(
        self,
        provider: ProviderName,
        exc: Exception,
    ) -> ProviderHealthSnapshot:
        disposition = classify_provider_failure(exc)
        now = self._now()

        with self._lock:
            state = self._states.setdefault(provider, _ProviderState())
            was_probe = state.status == "probing"
            state.probe_in_flight = False
            state.last_error_type = type(exc).__name__
            state.last_failure_at = now

            if not disposition.provider_level:
                # Bad input, truncated output and schema/JSON failures are request-specific.
                # They must not poison the provider for unrelated jobs.
                if state.status == "probing":
                    state.status = "healthy"
                    state.opened_until = None
                    state.reason = None
                return self._snapshot_locked(provider, state)

            state.consecutive_failures += 1
            state.reason = disposition.kind

            should_open = disposition.cooldown_seconds is not None
            if disposition.kind == "transient":
                should_open = was_probe or (
                    state.consecutive_failures >= _DEFAULT_TRANSIENT_FAILURE_THRESHOLD
                )

            if should_open:
                cooldown = disposition.cooldown_seconds or _DEFAULT_TRANSIENT_COOLDOWN
                cooldown = max(1.0, min(cooldown, _MAX_COOLDOWN_SECONDS))
                state.status = "cooldown"
                state.opened_until = now + timedelta(seconds=cooldown)
            else:
                state.status = "degraded"
                state.opened_until = None

            return self._snapshot_locked(provider, state)

    def snapshot(self, provider: ProviderName) -> ProviderHealthSnapshot:
        with self._lock:
            state = self._states.setdefault(provider, _ProviderState())
            return self._snapshot_locked(provider, state)

    def snapshots(self) -> list[ProviderHealthSnapshot]:
        with self._lock:
            providers: tuple[ProviderName, ...] = (
                "gemini",
                "groq",
                "openrouter",
                "openai",
            )
            return [
                self._snapshot_locked(
                    provider,
                    self._states.setdefault(provider, _ProviderState()),
                )
                for provider in providers
            ]

    def reset(self) -> None:
        with self._lock:
            self._states.clear()

    @staticmethod
    def _snapshot_locked(
        provider: ProviderName,
        state: _ProviderState,
    ) -> ProviderHealthSnapshot:
        return ProviderHealthSnapshot(
            provider=provider,
            status=state.status,
            consecutive_failures=state.consecutive_failures,
            opened_until=state.opened_until,
            reason=state.reason,
            last_error_type=state.last_error_type,
            last_failure_at=state.last_failure_at,
        )


def classify_provider_failure(exc: Exception) -> FailureDisposition:
    status_code = _status_code(exc)
    message = _exception_chain_text(exc)

    if _looks_request_specific(message, status_code):
        return FailureDisposition("request_specific", False, None)

    if _looks_output_specific(message):
        return FailureDisposition("output", False, None)

    if status_code in {401, 403} or any(
        token in message
        for token in (
            "invalid api key",
            "incorrect api key",
            "authentication",
            "unauthorized",
            "forbidden",
        )
    ):
        return FailureDisposition("auth", True, _DEFAULT_AUTH_COOLDOWN)

    if _looks_daily_quota(message):
        return FailureDisposition(
            "daily_quota",
            True,
            _retry_seconds(message) or _DEFAULT_DAILY_QUOTA_COOLDOWN,
        )

    if status_code == 429 or any(
        token in message
        for token in (
            "rate limit",
            "rate_limit",
            "too many requests",
            "tokens per minute",
            "requests per minute",
            "tpm",
            "rpm",
        )
    ):
        return FailureDisposition(
            "rate_limit",
            True,
            _retry_seconds(message) or _DEFAULT_RATE_LIMIT_COOLDOWN,
        )

    if status_code in {408, 425, 500, 502, 503, 504} or any(
        token in message
        for token in (
            "timed out",
            "timeout",
            "connection reset",
            "connection error",
            "temporarily unavailable",
            "service unavailable",
            "bad gateway",
            "gateway timeout",
        )
    ):
        return FailureDisposition("transient", True, _DEFAULT_TRANSIENT_COOLDOWN)

    return FailureDisposition("unknown", False, None)


def _exception_chain_text(exc: Exception) -> str:
    parts: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(str(current).lower())
        current = current.__cause__ or current.__context__
    return " | ".join(parts)


def _status_code(exc: Exception) -> int | None:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        value = getattr(current, "status_code", None) or getattr(current, "code", None)
        if isinstance(value, int):
            return value
        current = current.__cause__ or current.__context__
    return None


def _looks_daily_quota(message: str) -> bool:
    return any(
        token in message
        for token in (
            "daily quota",
            "per day",
            "per-day",
            "tokens per day",
            "requests per day",
            "free-models-per-day",
            "tpd",
            "perdayperprojectpermodel",
            "generaterequestsperdayperprojectpermodel",
            "free_tier_requests",
        )
    )


def _looks_request_specific(message: str, status_code: int | None) -> bool:
    if status_code == 413:
        return True
    return any(
        token in message
        for token in (
            "request too large",
            "context length",
            "maximum context",
            "context window",
            "prompt is too long",
            "input too long",
            "payload too large",
        )
    )


def _looks_output_specific(message: str) -> bool:
    return any(
        token in message
        for token in (
            "output token limit",
            "max_tokens",
            "max completion tokens",
            "truncated json",
            "invalid json",
            "json_validate_failed",
            "failed to validate json",
            "provider returned empty output",
            "provider returned no choices",
        )
    )


def _retry_seconds(message: str) -> float | None:
    reset = re.search(r"x-ratelimit-reset[^0-9]*(\d{10,13})", message, re.IGNORECASE)
    if reset:
        raw = int(reset.group(1))
        timestamp = raw / 1000 if raw >= 10_000_000_000 else float(raw)
        delta = timestamp - datetime.now(UTC).timestamp()
        if 1 <= delta <= _MAX_COOLDOWN_SECONDS:
            return delta

    duration = re.search(
        r"(?:try again|retry|available again)[^0-9]*"
        r"(?:(\d+(?:\.\d+)?)h)?\s*"
        r"(?:(\d+(?:\.\d+)?)m)?\s*"
        r"(?:(\d+(?:\.\d+)?)s)?",
        message,
        re.IGNORECASE,
    )
    if duration and any(duration.groups()):
        hours = float(duration.group(1) or 0)
        minutes = float(duration.group(2) or 0)
        seconds = float(duration.group(3) or 0)
        value = (hours * 3600) + (minutes * 60) + seconds
        if value > 0:
            return min(value, _MAX_COOLDOWN_SECONDS)

    retry_after = re.search(
        r"retry(?:delay|[-_ ]after)[^0-9]*(\d+(?:\.\d+)?)s?",
        message,
        re.IGNORECASE,
    )
    if retry_after:
        return min(float(retry_after.group(1)), _MAX_COOLDOWN_SECONDS)

    return None


_provider_health = ProviderHealthRegistry()


def get_provider_health() -> ProviderHealthRegistry:
    return _provider_health


def reset_provider_health_for_tests() -> None:
    _provider_health.reset()
