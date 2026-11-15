from types import MethodType

import pytest

from app.services.ai_fallback import AllAIProvidersUnavailable
from app.services.requirement_extraction import (
    GeminiRequirementExtractor,
    RequirementExtractionError,
)


@pytest.mark.asyncio
async def test_truncated_opportunity_chunk_is_split_and_all_parts_kept() -> None:
    extractor = object.__new__(GeminiRequirementExtractor)
    calls: list[int] = []

    async def extract_one(self, source_text, *, chunk_index, chunk_count):
        calls.append(len(source_text))
        if len(source_text) > 1800:
            raise RequirementExtractionError("Fallback providers failed") from (
                AllAIProvidersUnavailable("openrouter: AIOutputTruncated")
            )
        return source_text

    extractor._extract_one = MethodType(extract_one, extractor)
    source = ("First requirement about accounting experience.\n" * 100)
    parts = await extractor._extract_with_adaptive_split(
        source, chunk_index=1, chunk_count=1
    )

    assert len(parts) >= 2
    assert all(len(part) <= 1800 for part in parts)
    assert "".join(part.replace("\n", "") for part in parts) == source.replace("\n", "")
    assert calls[0] == len(source)


@pytest.mark.asyncio
async def test_provider_quota_failure_is_not_split() -> None:
    extractor = object.__new__(GeminiRequirementExtractor)
    calls = 0

    async def extract_one(self, source_text, *, chunk_index, chunk_count):
        nonlocal calls
        calls += 1
        raise RequirementExtractionError("Fallback providers failed") from (
            AllAIProvidersUnavailable("groq: RateLimitError; openrouter: circuit_open")
        )

    extractor._extract_one = MethodType(extract_one, extractor)
    with pytest.raises(RequirementExtractionError):
        await extractor._extract_with_adaptive_split(
            "This is a sample line.\n" * 200, chunk_index=1, chunk_count=1
        )
    assert calls == 1


@pytest.mark.asyncio
async def test_small_truncated_section_does_not_retry_forever() -> None:
    extractor = object.__new__(GeminiRequirementExtractor)
    calls = 0

    async def extract_one(self, source_text, *, chunk_index, chunk_count):
        nonlocal calls
        calls += 1
        raise RequirementExtractionError("Fallback providers failed") from (
            AllAIProvidersUnavailable("openrouter: AIOutputTruncated")
        )

    extractor._extract_one = MethodType(extract_one, extractor)
    with pytest.raises(RequirementExtractionError):
        await extractor._extract_with_adaptive_split(
            "line\n" * 50, chunk_index=1, chunk_count=1
        )
    assert calls == 1
