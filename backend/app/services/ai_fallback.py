import base64
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings

logger = logging.getLogger(__name__)


class AllAIProvidersUnavailable(RuntimeError):
    pass


class AIOutputTruncated(RuntimeError):
    pass


class FallbackAI:
    GROQ_MODELS = (
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instant",
    )

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        logger.info(
            "AI fallback configuration: groq=%s openrouter=%s openai=%s",
            bool(self.settings.groq_api_key),
            bool(self.settings.openrouter_api_key),
            bool(self.settings.openai_api_key),
        )

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.groq_api_key
            or self.settings.openrouter_api_key
            or self.settings.openai_api_key
        )

    @staticmethod
    def _is_hard_rate_limit(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        message = str(exc).lower()
        return status_code == 429 or any(
            token in message
            for token in (
                "rate limit",
                "rate_limit",
                "tokens per minute",
                "tpm",
                "quota",
                "too many requests",
            )
        )

    async def extract_image_text(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        label: str,
    ) -> tuple[str, str]:
        """Recover visible document text from an image using configured multimodal fallbacks."""
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{encoded}"
        prompt = (
            "Transcribe all readable text from this professional document image. "
            "Preserve names, dates, qualifications, employers, project names, roles, "
            "certifications, tables, and headings. Do not summarize or invent text. "
            f"Image label: {label}."
        )
        errors: list[str] = []

        if self.settings.openrouter_api_key:
            try:
                model = self.settings.openrouter_model.strip() or "openrouter/free"
                client = AsyncOpenAI(
                    api_key=self.settings.openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1",
                    timeout=180.0,
                    max_retries=1,
                    default_headers={
                        "HTTP-Referer": "https://capability-flow.onrender.com",
                        "X-Title": "Capability Flow",
                    },
                )
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_url},
                                },
                            ],
                        }
                    ],
                    temperature=0.0,
                    max_tokens=3000,
                )
                text = self._decode_text_response(response)
                logger.info(
                    "Image text recovery succeeded: provider=openrouter model=%s label=%s",
                    model,
                    label,
                )
                return text, f"openrouter:{model}:vision"
            except Exception as exc:
                logger.warning(
                    "OpenRouter image text recovery failed: label=%s error=%s",
                    label,
                    str(exc),
                )
                errors.append(f"openrouter: {type(exc).__name__}")

        if self.settings.groq_api_key:
            try:
                client = AsyncOpenAI(
                    api_key=self.settings.groq_api_key,
                    base_url="https://api.groq.com/openai/v1",
                    timeout=150.0,
                    max_retries=1,
                )
                models = await client.models.list()
                vision_models = [
                    item.id
                    for item in models.data
                    if any(token in item.id.lower() for token in ("vision", "scout", "maverick"))
                ]
                if not vision_models:
                    raise ValueError("Groq exposes no multimodal model")
                last_error: Exception | None = None
                for model in vision_models[:3]:
                    try:
                        response = await client.chat.completions.create(
                            model=model,
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {"url": data_url},
                                        },
                                    ],
                                }
                            ],
                            temperature=0.0,
                            max_tokens=3000,
                        )
                        text = self._decode_text_response(response)
                        logger.info(
                            "Image text recovery succeeded: provider=groq model=%s label=%s",
                            model,
                            label,
                        )
                        return text, f"groq:{model}:vision"
                    except Exception as exc:
                        last_error = exc
                        if self._is_hard_rate_limit(exc):
                            logger.warning(
                                "Groq vision hard quota/rate limit detected; stopping model retries"
                            )
                            break
                if last_error is not None:
                    raise last_error
            except Exception as exc:
                logger.warning(
                    "Groq image text recovery failed: label=%s error=%s",
                    label,
                    str(exc),
                )
                errors.append(f"groq: {type(exc).__name__}")

        if self.settings.openai_api_key:
            try:
                return await self._extract_image_text_openai(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    label=label,
                    prompt=prompt,
                )
            except Exception as exc:
                logger.warning(
                    "OpenAI image text recovery failed: label=%s error=%s",
                    label,
                    str(exc),
                )
                errors.append(f"openai: {type(exc).__name__}")

        if not errors:
            raise AllAIProvidersUnavailable("No multimodal fallback provider is configured")
        raise AllAIProvidersUnavailable("; ".join(errors))

    async def _extract_image_text_openai(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        label: str,
        prompt: str,
    ) -> tuple[str, str]:
        key = self.settings.openai_api_key
        if not key:
            raise AllAIProvidersUnavailable("OpenAI is not configured")

        model = self.settings.openai_model.strip() or "gpt-5.6-luna"
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{encoded}"
        client = AsyncOpenAI(
            api_key=key,
            timeout=180.0,
            max_retries=1,
        )
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
            reasoning_effort="none",
            max_completion_tokens=3000,
        )
        text = self._decode_text_response(response)
        logger.info(
            "Image text recovery succeeded: provider=openai model=%s label=%s",
            model,
            label,
        )
        return text, f"openai:{model}:vision"

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        # Keep the free providers tightly bounded. OpenAI Luna is the paid safety net
        # and receives a larger ceiling only after the free providers are exhausted.
        free_max_tokens = min(max_tokens, 3500)
        errors: list[str] = []

        if self.settings.groq_api_key:
            try:
                return await self._generate_groq(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=free_max_tokens,
                )
            except Exception as exc:
                logger.warning(
                    "AI fallback provider exhausted: provider=groq error=%s",
                    str(exc),
                )
                errors.append(f"groq: {type(exc).__name__}")

        if self.settings.openrouter_api_key:
            try:
                return await self._generate_openrouter(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=free_max_tokens,
                )
            except Exception as exc:
                logger.warning(
                    "AI fallback provider exhausted: provider=openrouter error=%s",
                    str(exc),
                )
                errors.append(f"openrouter: {type(exc).__name__}")

        if self.settings.openai_api_key:
            try:
                return await self._generate_openai(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                logger.warning(
                    "AI fallback provider exhausted: provider=openai error=%s",
                    str(exc),
                )
                errors.append(f"openai: {type(exc).__name__}")

        if not errors:
            raise AllAIProvidersUnavailable("No fallback AI provider is configured")
        raise AllAIProvidersUnavailable("; ".join(errors))

    async def _generate_openai(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        key = self.settings.openai_api_key
        if not key:
            raise AllAIProvidersUnavailable("OpenAI is not configured")

        model = self.settings.openai_model.strip() or "gpt-5.6-luna"
        client = AsyncOpenAI(
            api_key=key,
            timeout=180.0,
            max_retries=1,
        )

        # Luna is only reached after the free providers fail. Give structured output
        # enough room to close the JSON object, and retry once if the first response
        # is explicitly length-limited or arrives as truncated JSON.
        initial_limit = max(max_tokens, 6000)
        retry_limit = max(initial_limit * 2, 12000)
        token_limits = (initial_limit, retry_limit)

        for attempt, token_limit in enumerate(token_limits, start=1):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "developer", "content": system_prompt},
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
                    reasoning_effort="none",
                    max_completion_tokens=token_limit,
                )
                data = self._decode_response(response)
                logger.info(
                    "AI fallback succeeded with provider=openai model=%s "
                    "attempt=%s max_completion_tokens=%s",
                    model,
                    attempt,
                    token_limit,
                )
                return data, f"openai:{model}"
            except (AIOutputTruncated, json.JSONDecodeError) as exc:
                if attempt >= len(token_limits):
                    raise
                logger.warning(
                    "OpenAI structured output was incomplete; retrying once with "
                    "a larger output budget: model=%s next_max_completion_tokens=%s "
                    "error=%s",
                    model,
                    retry_limit,
                    str(exc),
                )

        raise AllAIProvidersUnavailable("OpenAI did not return usable structured output")

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
            logger.warning(
                "Groq model discovery failed; using preferred candidates: %s",
                str(exc),
            )

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
                logger.info(
                    "AI fallback succeeded with provider=groq model=%s",
                    model,
                )
                return data, f"groq:{model}"
            except Exception as exc:
                logger.warning("Groq model failed: model=%s error=%s", model, str(exc))
                errors.append(f"{model}: {type(exc).__name__}")
                if self._is_hard_rate_limit(exc):
                    logger.warning(
                        "Groq hard quota/rate limit detected; switching to the next "
                        "fallback provider"
                    )
                    break

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
            logger.info(
                "AI fallback succeeded with provider=openrouter model=%s",
                model,
            )
            return data, f"openrouter:{model}"
        except Exception as structured_exc:
            logger.warning(
                "OpenRouter structured-output attempt failed: model=%s error=%s",
                model,
                str(structured_exc),
            )
            if self._is_hard_rate_limit(structured_exc):
                logger.warning(
                    "OpenRouter hard quota/rate limit detected; switching to OpenAI Luna"
                )
                raise

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
            "AI fallback succeeded with provider=openrouter model=%s mode=json_object",
            model,
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
    def _decode_text_response(response: Any) -> str:
        if not getattr(response, "choices", None):
            raise ValueError("provider returned no choices")
        content = response.choices[0].message.content
        if not content or not str(content).strip():
            raise ValueError("provider returned empty text output")
        return str(content).strip()

    @staticmethod
    def _decode_response(response: Any) -> dict[str, Any]:
        if not getattr(response, "choices", None):
            raise ValueError("provider returned no choices")

        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason in {"length", "max_tokens"}:
            raise AIOutputTruncated(
                "provider stopped because the output token limit was reached"
            )

        message = choice.message
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
