import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings

logger = logging.getLogger(__name__)


class AllAIProvidersUnavailable(RuntimeError):
    pass


class FallbackAI:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.groq_api_key or self.settings.openrouter_api_key)

    async def generate_json(
        self, *, system_prompt: str, user_prompt: str, schema: dict[str, Any], max_tokens: int
    ) -> tuple[dict[str, Any], str]:
        providers: list[tuple[str, str, str, str]] = []
        if self.settings.groq_api_key:
            providers.append(
                (
                    "groq",
                    self.settings.groq_api_key,
                    "https://api.groq.com/openai/v1",
                    self.settings.groq_model,
                )
            )
        if self.settings.openrouter_api_key:
            providers.append(
                (
                    "openrouter",
                    self.settings.openrouter_api_key,
                    "https://openrouter.ai/api/v1",
                    self.settings.openrouter_model,
                )
            )
        if not providers:
            raise AllAIProvidersUnavailable("No fallback AI provider is configured")

        errors: list[str] = []
        schema_text = json.dumps(schema, separators=(",", ":"))
        guarded_prompt = (
            f"{user_prompt}\n\nReturn one JSON object only. It must conform to this JSON Schema:\n"
            f"{schema_text}"
        )
        for name, key, base_url, model in providers:
            try:
                client = AsyncOpenAI(api_key=key, base_url=base_url, timeout=90.0, max_retries=1)
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": guarded_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("provider returned empty output")
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("provider did not return a JSON object")
                logger.info("AI fallback succeeded with provider=%s model=%s", name, model)
                return data, f"{name}:{model}"
            except Exception as exc:
                logger.warning("AI fallback provider failed: provider=%s error=%s", name, str(exc))
                errors.append(f"{name}: {type(exc).__name__}")
        raise AllAIProvidersUnavailable("; ".join(errors) or "All fallback providers failed")
