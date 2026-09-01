import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings

logger = logging.getLogger(__name__)


class AllAIProvidersUnavailable(RuntimeError):
    pass


class FallbackAI:
    GROQ_MODELS = (
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instant",
    )

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.groq_api_key or self.settings.openrouter_api_key)

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        errors: list[str] = []

        if self.settings.groq_api_key:
            try:
                return await self._generate_groq(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                logger.warning("AI fallback provider exhausted: provider=groq error=%s", str(exc))
                errors.append(f"groq: {type(exc).__name__}")

        if self.settings.openrouter_api_key:
            try:
                return await self._generate_openrouter(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                logger.warning(
                    "AI fallback provider exhausted: provider=openrouter error=%s", str(exc)
                )
                errors.append(f"openrouter: {type(exc).__name__}")

        if not errors:
            raise AllAIProvidersUnavailable("No fallback AI provider is configured")
        raise AllAIProvidersUnavailable("; ".join(errors))

    async def _generate_groq(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        key = self.settings.groq_api_key
        if not key:
            raise AllAIProvidersUnavailable("Groq is not configured")

        client = AsyncOpenAI(
            api_key=key,
            base_url="https://api.groq.com/openai/v1",
            timeout=150.0,
            max_retries=1,
        )
        configured = self.settings.groq_model.strip()
        candidates = list(dict.fromkeys((configured, *self.GROQ_MODELS)))

        try:
            models = await client.models.list()
            available = {item.id for item in models.data}
            usable = [model for model in candidates if model in available]
            if usable:
                candidates = usable
            logger.info(
                "Groq model discovery complete: preferred=%s candidates=%s",
                configured,
                candidates,
            )
        except Exception as exc:
            logger.warning("Groq model discovery failed; using preferred candidates: %s", str(exc))

        errors: list[str] = []
        for model in candidates:
            try:
                data = await self._chat_json(
                    client=client,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                    require_parameters=False,
                )
                logger.info("AI fallback succeeded with provider=groq model=%s", model)
                return data, f"groq:{model}"
            except Exception as exc:
                logger.warning("Groq model failed: model=%s error=%s", model, str(exc))
                errors.append(f"{model}: {type(exc).__name__}")

        raise AllAIProvidersUnavailable("Groq models failed: " + "; ".join(errors))

    async def _generate_openrouter(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        key = self.settings.openrouter_api_key
        if not key:
            raise AllAIProvidersUnavailable("OpenRouter is not configured")

        model = self.settings.openrouter_model.strip() or "openrouter/free"
        client = AsyncOpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            timeout=180.0,
            max_retries=1,
            default_headers={
                "HTTP-Referer": "https://capability-flow.onrender.com",
                "X-Title": "Capability Flow",
            },
        )

        # First request forces OpenRouter's free router to choose only a model that
        # supports structured JSON Schema output.
        try:
            data = await self._chat_json(
                client=client,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                max_tokens=max_tokens,
                require_parameters=True,
            )
            logger.info("AI fallback succeeded with provider=openrouter model=%s", model)
            return data, f"openrouter:{model}"
        except Exception as structured_exc:
            logger.warning(
                "OpenRouter structured-output attempt failed: model=%s error=%s",
                model,
                str(structured_exc),
            )

        # Some free models temporarily expose JSON mode without strict schema mode.
        # A second request keeps the application useful while downstream Pydantic
        # validation remains the final safety gate.
        data = await self._chat_json_object(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            max_tokens=max_tokens,
        )
        logger.info(
            "AI fallback succeeded with provider=openrouter model=%s mode=json_object", model
        )
        return data, f"openrouter:{model}"

    async def _chat_json(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
        require_parameters: bool,
    ) -> dict[str, Any]:
        extra_body: dict[str, Any] | None = None
        if require_parameters:
            extra_body = {"provider": {"require_parameters": True}}

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "capability_flow_result",
                    "strict": False,
                    "schema": schema,
                },
            },
            temperature=0.1,
            max_tokens=max_tokens,
            extra_body=extra_body,
        )
        return self._decode_response(response)

    async def _chat_json_object(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        schema_text = json.dumps(schema, separators=(",", ":"))
        guarded_prompt = (
            f"{user_prompt}\n\nReturn exactly one JSON object and no prose. "
            "The object must conform to this JSON Schema:\n"
            f"{schema_text}"
        )
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
        return self._decode_response(response)

    @staticmethod
    def _decode_response(response: Any) -> dict[str, Any]:
        if not getattr(response, "choices", None):
            raise ValueError("provider returned no choices")

        message = response.choices[0].message
        content = message.content
        if not content or not str(content).strip():
            refusal = getattr(message, "refusal", None)
            if refusal:
                raise ValueError(f"provider refused the request: {refusal}")
            raise ValueError("provider returned empty output")

        cleaned = str(content).strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("provider did not return a JSON object")
        return data
