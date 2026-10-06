from types import SimpleNamespace

from app.services.requirement_extraction import GeminiRequirementExtractor


def test_fallback_chunking_clamps_oversized_deployment_config() -> None:
    extractor = object.__new__(GeminiRequirementExtractor)
    extractor.app_settings = SimpleNamespace(gemini_api_key=None)
    extractor.opportunity_settings = SimpleNamespace(
        opportunity_analysis_chunk_characters=100_000,
        opportunity_analysis_chunk_overlap=5_000,
    )

    chunks = extractor._chunk_source("A" * 18_000)

    assert len(chunks) >= 4
    assert max(len(chunk) for chunk in chunks) <= 5_000


def test_gemini_chunking_keeps_configured_large_chunk() -> None:
    extractor = object.__new__(GeminiRequirementExtractor)
    extractor.app_settings = SimpleNamespace(gemini_api_key="configured")
    extractor.opportunity_settings = SimpleNamespace(
        opportunity_analysis_chunk_characters=20_000,
        opportunity_analysis_chunk_overlap=1_000,
    )

    chunks = extractor._chunk_source("A" * 18_000)

    assert chunks == ["A" * 18_000]
