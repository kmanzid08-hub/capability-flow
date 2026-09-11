from __future__ import annotations

from enum import StrEnum


class AIRequestMode(StrEnum):
    QUICK = "quick"
    PROFILE = "profile"
    OPPORTUNITY = "opportunity"


PROVIDER_ORDER = {
    AIRequestMode.QUICK: ("groq", "openrouter", "openai"),
    AIRequestMode.PROFILE: ("groq", "openrouter", "openai"),
    AIRequestMode.OPPORTUNITY: ("openai", "openrouter", "groq"),
}


def choose_mode(
    estimated_tokens: int, default: AIRequestMode = AIRequestMode.QUICK
) -> AIRequestMode:
    if estimated_tokens > 5000:
        return AIRequestMode.OPPORTUNITY
    return default
