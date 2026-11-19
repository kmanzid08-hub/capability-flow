"""An AI quota interruption never destroys already verified tender chunks."""
from __future__ import annotations

from types import MethodType, SimpleNamespace

import pytest

from app.schemas.opportunity import ExtractedOpportunity
from app.services.requirement_extraction import (
    GeminiRequirementExtractor,
    RequirementExtractionError,
)


def _result(label: str) -> ExtractedOpportunity:
    return ExtractedOpportunity.model_validate(
        {"summary": label, "roles": []}
    )


@pytest.mark.asyncio
async def test_quota_interruption_preserves_only_completed_validated_chunks() -> None:
    extractor = object.__new__(GeminiRequirementExtractor)
    extractor.opportunity_settings = SimpleNamespace(
        opportunity_max_source_characters=100_000,
        opportunity_analysis_chunk_characters=3000,
        opportunity_analysis_chunk_overlap=0,
    )
    sections = ["First section " * 250, "Second section " * 250, "Third section " * 250]
    source = "\n".join(sections)
    chunks = extractor._chunk_source(source)
    assert len(chunks) >= 2
    called: list[int] = []
    saved: dict[int, list[ExtractedOpportunity]] = {}

    async def first_pass(self, text, *, chunk_index, chunk_count, depth=0):
        called.append(chunk_index)
        if chunk_index == 2:
            raise RequirementExtractionError("All AI providers unavailable")
        return [_result(f"completed {chunk_index}")]

    async def persist(index: int, parts: list[ExtractedOpportunity]):
        saved[index] = parts

    extractor._extract_with_adaptive_split = MethodType(first_pass, extractor)
    with pytest.raises(RequirementExtractionError, match="providers unavailable"):
        await extractor.extract(source, on_chunk_completed=persist)
    assert list(saved) == [1]
    assert called == [1, 2]

    completed_indices: list[int] = []

    async def second_pass(self, text, *, chunk_index, chunk_count, depth=0):
        completed_indices.append(chunk_index)
        return [_result(f"completed {chunk_index}")]

    extractor._extract_with_adaptive_split = MethodType(second_pass, extractor)
    result = await extractor.extract(
        source, completed_chunks=saved, on_chunk_completed=persist
    )
    assert result is not None
    assert 1 not in completed_indices
    assert completed_indices == list(range(2, len(chunks) + 1))
    assert len(saved) == len(chunks)


@pytest.mark.asyncio
async def test_invalid_or_out_of_range_cache_entries_are_not_reused() -> None:
    extractor = object.__new__(GeminiRequirementExtractor)
    extractor.opportunity_settings = SimpleNamespace(
        opportunity_max_source_characters=100000,
        opportunity_analysis_chunk_characters=3000,
        opportunity_analysis_chunk_overlap=0,
    )
    calls = []

    async def one(self, text, *, chunk_index, chunk_count, depth=0):
        calls.append(chunk_index)
        return [_result("fresh")]

    extractor._extract_with_adaptive_split = MethodType(one, extractor)
    await extractor.extract(
        "Source text",
        completed_chunks={-1: [_result("not valid")], 99: [_result("stale")]},
    )
    assert calls == [1]
