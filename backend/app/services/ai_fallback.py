import base64
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings
from app.services.ai_provider_health import ProviderName, get_provider_health

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
        self.provider_health = get_provider_health()
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
        # A model stopping because its response hit max_tokens is recoverable:
        # another model or a larger output budget may still succeed.
        if isinstance(exc, AIOutputTruncated):
            return False

        status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        message = str(exc).lower()
        return status_code in (413, 429) or any(
            token in message
            for token in (
                "rate limit",
                "rate_limit",
                "tokens per minute",
                "tpm",
                "quota",
                "too many requests",
                "request too large",
                "context length",
                "maximum context",
            )
        )

    async def extract_image_text(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        label: str,
    ) -> tuple[str, str]:
        """Recover visible document text from an image using healthy multimodal providers."""
        prompt = (
            "Transcribe all readable text from this professional document image. "
            "Preserve names, dates, qualifications, employers, project names, roles, "
            "certifications, tables, and headings. Do not summarize or invent text. "
            f"Image label: {label}."
        )
        errors: list[str] = []
        providers: tuple[ProviderName, ...] = ("openrouter", "groq", "openai")

        for provider in providers:
            configured = {
                "openrouter": bool(self.settings.openrouter_api_key),
                "groq": bool(self.settings.groq_api_key),
                "openai": bool(self.settings.openai_api_key),
            }[provider]
            if not configured:
                continue

            if not self.provider_health.before_call(provider):
                snapshot = self.provider_health.snapshot(provider)
                logger.warning(
                    "Skipping AI vision provider while circuit is open: "
                    "provider=%s status=%s reason=%s opened_until=%s",
                    provider,
                    snapshot.status,
                    snapshot.reason,
                    snapshot.opened_until,
                )
                errors.append(f"{provider}: circuit_open")
                continue

            try:
                if provider == "openrouter":
                    result = await self._extract_image_text_openrouter(
                        image_bytes=image_bytes,
                        mime_type=mime_type,
                        label=label,
                        prompt=prompt,
                    )
                elif provider == "groq":
                    result = await self._extract_image_text_groq(
                        image_bytes=image_bytes,
                        mime_type=mime_type,
                        label=label,
                        prompt=prompt,
                    )
                else:
                    result = await self._extract_image_text_openai(
                        image_bytes=image_bytes,
                        mime_type=mime_type,
                        label=label,
                        prompt=prompt,
                    )
            except Exception as exc:
                snapshot = self.provider_health.record_failure(provider, exc)
                logger.warning(
                    "AI image text recovery provider failed: provider=%s label=%s "
                    "health=%s reason=%s error=%s",
                    provider,
                    label,
                    snapshot.status,
                    snapshot.reason,
                    str(exc),
                )
                errors.append(f"{provider}: {type(exc).__name__}")
                continue

            self.provider_health.record_success(provider)
            return result

        if not errors:
            raise AllAIProvidersUnavailable("No multimodal fallback provider is configured")
        raise AllAIProvidersUnavailable("; ".join(errors))

    async def _extract_image_text_openrouter(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        label: str,
        prompt: str,
    ) -> tuple[str, str]:
        key = self.settings.openrouter_api_key
        if not key:
            raise AllAIProvidersUnavailable("OpenRouter is not configured")

        model = self.settings.openrouter_model.strip() or "openrouter/free"
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{encoded}"
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
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
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

    async def _extract_image_text_groq(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        label: str,
        prompt: str,
    ) -> tuple[str, str]:
        key = self.settings.groq_api_key
        if not key:
            raise AllAIProvidersUnavailable("Groq is not configured")

        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{encoded}"
        client = AsyncOpenAI(
            api_key=key,
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
                                {"type": "image_url", "image_url": {"url": data_url}},
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
        raise ValueError("Groq vision models returned no usable response")

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

    @staticmethod
    def _profile_result_has_evidence(data: dict[str, Any]) -> bool:
        evidence = data.get("evidence")
        if not isinstance(evidence, list):
            return False
        return any(
            isinstance(item, dict)
            and str(item.get("category") or "").strip()
            and str(item.get("title") or "").strip()
            for item in evidence
        )

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
        mode: str = "quick",
    ) -> tuple[dict[str, Any], str]:
        # Preserve the free-first provider order while respecting provider-specific
        # request limits. Groq free/on-demand tiers can reject a request when input
        # tokens + requested output exceed the model's TPM allowance, so opportunity
        # extraction uses a conservative Groq budget. OpenRouter keeps the caller's
        # larger structured-output budget.
        if mode == "profile":
            groq_max_tokens = min(max_tokens, 3500)
            openrouter_max_tokens = min(max_tokens, 3500)
        elif mode == "opportunity":
            groq_max_tokens = min(max_tokens, 1600)
            openrouter_max_tokens = min(max_tokens, 3000)
        else:
            groq_max_tokens = min(max_tokens, 4000)
            openrouter_max_tokens = min(max_tokens, 6000)
        errors: list[str] = []
        providers: tuple[ProviderName, ...] = ("groq", "openrouter", "openai")
        last_profile_result: tuple[dict[str, Any], str] | None = None

        for provider in providers:
            configured = {
                "groq": bool(self.settings.groq_api_key),
                "openrouter": bool(self.settings.openrouter_api_key),
                "openai": bool(self.settings.openai_api_key),
            }[provider]
            if not configured:
                continue

            if not self.provider_health.before_call(provider):
                snapshot = self.provider_health.snapshot(provider)
                logger.warning(
                    "Skipping AI provider while circuit is open: provider=%s status=%s "
                    "reason=%s opened_until=%s",
                    provider,
                    snapshot.status,
                    snapshot.reason,
                    snapshot.opened_until,
                )
                errors.append(f"{provider}: circuit_open")
                continue

            try:
                if provider == "groq":
                    result = await self._generate_groq(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        schema=schema,
                        max_tokens=groq_max_tokens,
                        mode=mode,
                    )
                elif provider == "openrouter":
                    result = await self._generate_openrouter(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        schema=schema,
                        max_tokens=openrouter_max_tokens,
                        mode=mode,
                    )
                else:
                    result = await self._generate_openai(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        schema=schema,
                        max_tokens=max_tokens,
                        mode=mode,
                    )
            except Exception as exc:
                snapshot = self.provider_health.record_failure(provider, exc)
                logger.warning(
                    "AI fallback provider exhausted: provider=%s health=%s reason=%s error=%s",
                    provider,
                    snapshot.status,
                    snapshot.reason,
                    str(exc),
                )
                errors.append(f"{provider}: {type(exc).__name__}")
                continue

            # A valid response proves the provider itself is healthy even when a profile
            # chunk legitimately contains no reviewable evidence (for example a cover page).
            self.provider_health.record_success(provider)

            if mode == "profile" and not self._profile_result_has_evidence(result[0]):
                last_profile_result = result
                logger.info(
                    "Profile fallback returned a valid empty extraction; trying next provider: "
                    "provider=%s",
                    provider,
                )
                continue

            return result

        # An empty profile chunk is not a provider outage. If every reachable provider
        # returned a valid empty result, let the caller merge it with the other chunks.
        if last_profile_result is not None:
            return last_profile_result

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
        mode: str = "quick",
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
        if mode == "profile":
            # Profile chunks use the compact evidence schema, so keep the output
            # deliberately small. This prevents Luna from spending its budget
            # constructing a full profile object for every chunk.
            initial_limit = min(max_tokens, 900)
            retry_limit = 1400
        else:
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
        mode: str = "quick",
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
        if mode == "opportunity":
            # The 20B model repeatedly exhausts its request/output allowance on
            # realistic TOR extraction. Prefer 120B and do not send opportunity
            # extraction to 20B at all.
            opportunity_candidates = (
                "openai/gpt-oss-120b",
                configured if configured != "openai/gpt-oss-20b" else "",
                "llama-3.1-8b-instant",
            )
            candidates = list(dict.fromkeys(model for model in opportunity_candidates if model))
        else:
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
            structured_error: Exception | None = None
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
                    "AI fallback succeeded with provider=groq model=%s mode=json_schema",
                    model,
                )
                return data, f"groq:{model}"
            except Exception as exc:
                structured_error = exc
                logger.warning(
                    "Groq structured-output attempt failed: model=%s error=%s",
                    model,
                    str(exc),
                )
                errors.append(f"{model}/json_schema: {type(exc).__name__}: {str(exc)}")

                # Groq can reject JSON Schema mode even when it generated a complete
                # object. Its API error may include that object in failed_generation.
                # Recover and parse it locally before spending another provider call.
                if mode == "opportunity":
                    recovered = self._recover_failed_generation_json(exc)
                    if recovered is not None:
                        logger.info(
                            "Recovered Groq opportunity JSON from failed_generation: model=%s",
                            model,
                        )
                        return recovered, f"groq:{model}:recovered"

            status_code = getattr(structured_error, "status_code", None) or getattr(
                structured_error, "code", None
            )
            if status_code in (413, "413"):
                logger.warning(
                    "Groq model request exceeded that model's token allowance; "
                    "trying the next Groq model"
                )
                continue

            if structured_error is not None and self._is_hard_rate_limit(structured_error):
                logger.warning(
                    "Groq hard quota/rate limit detected; switching to the next fallback provider"
                )
                break

            # For opportunity extraction, embedding the full schema in a second
            # JSON-object request materially increases prompt size and has already
            # pushed Groq requests over provider limits. If failed_generation could
            # not be recovered, move to another model/provider instead.
            if mode == "opportunity":
                logger.warning(
                    "Skipping Groq JSON-object retry for opportunity extraction: model=%s",
                    model,
                )
                continue

            # Other compact modes retain the same-model JSON Object recovery.
            json_object_tokens = max_tokens
            try:
                data = await self._chat_json_object(
                    client=client,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=json_object_tokens,
                )
                logger.info(
                    "AI fallback succeeded with provider=groq model=%s mode=json_object",
                    model,
                )
                return data, f"groq:{model}"
            except Exception as exc:
                logger.warning(
                    "Groq JSON-object recovery failed: model=%s error=%s",
                    model,
                    str(exc),
                )
                errors.append(f"{model}/json_object: {type(exc).__name__}: {str(exc)}")

                status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                if status_code in (413, "413"):
                    continue
                if self._is_hard_rate_limit(exc):
                    logger.warning(
                        "Groq hard quota/rate limit detected during JSON-object recovery; "
                        "switching to the next fallback provider"
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
        mode: str = "quick",
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

        structured_error: Exception | None = None

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
        except Exception as exc:
            structured_error = exc
            logger.warning(
                "OpenRouter structured-output attempt failed: model=%s error=%s",
                model,
                str(exc),
            )

        if isinstance(structured_error, AIOutputTruncated):
            retry_tokens = (
                min(4000, max(max_tokens + 1000, 3000))
                if mode == "opportunity"
                else min(8192, max(max_tokens * 2, 6000))
            )
            try:
                data = await self._chat_json(
                    client=client,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=retry_tokens,
                    require_parameters=True,
                )
                logger.info(
                    "AI fallback succeeded with provider=openrouter model=%s "
                    "after output-budget retry max_tokens=%s",
                    model,
                    retry_tokens,
                )
                return data, f"openrouter:{model}"
            except Exception as retry_exc:
                structured_error = retry_exc
                logger.warning(
                    "OpenRouter larger structured-output retry failed: "
                    "model=%s max_tokens=%s error=%s",
                    model,
                    retry_tokens,
                    str(retry_exc),
                )

        if structured_error is not None and self._is_hard_rate_limit(structured_error):
            logger.warning(
                "OpenRouter quota/context limit detected; switching to the next configured provider"
            )
            raise structured_error

        # Some free models expose JSON mode even when JSON Schema mode is unstable.
        # Opportunity extraction gets a larger second-chance budget because the
        # result can contain many roles and requirements.
        json_object_tokens = (
            min(4000, max(max_tokens, 3000)) if mode == "opportunity" else max_tokens
        )
        data = await self._chat_json_object(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            max_tokens=json_object_tokens,
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
    def _failed_generation_text(exc: Exception) -> str | None:
        def extract(payload: Any) -> str | None:
            if not isinstance(payload, dict):
                return None
            nested = payload.get("error")
            if isinstance(nested, dict):
                value = nested.get("failed_generation")
                if isinstance(value, str) and value.strip():
                    return value.strip()
            value = payload.get("failed_generation")
            if isinstance(value, str) and value.strip():
                return value.strip()
            return None

        recovered = extract(getattr(exc, "body", None))
        if recovered is not None:
            return recovered

        response = getattr(exc, "response", None)
        if response is not None:
            try:
                recovered = extract(response.json())
            except Exception:
                recovered = None
            if recovered is not None:
                return recovered
        return None

    @classmethod
    def _recover_failed_generation_json(cls, exc: Exception) -> dict[str, Any] | None:
        text = cls._failed_generation_text(exc)
        if text is None:
            return None
        try:
            return cls._decode_json_text(text)
        except (json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def _decode_json_text(content: str) -> dict[str, Any]:
        cleaned = content.strip()
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

    @staticmethod
    def _decode_response(response: Any) -> dict[str, Any]:
        if not getattr(response, "choices", None):
            raise ValueError("provider returned no choices")

        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason in {"length", "max_tokens"}:
            raise AIOutputTruncated("provider stopped because the output token limit was reached")

        message = choice.message
        content = message.content
        if not content or not str(content).strip():
            refusal = getattr(message, "refusal", None)
            if refusal:
                raise ValueError(f"provider refused the request: {refusal}")
            raise ValueError("provider returned empty output")

        return FallbackAI._decode_json_text(str(content))
