from types import SimpleNamespace

from app.services.requirement_extraction import GeminiRequirementExtractor


def _extractor() -> GeminiRequirementExtractor:
    extractor = object.__new__(GeminiRequirementExtractor)
    extractor.app_settings = SimpleNamespace(
        gemini_api_key="configured",
        ai_model="gemini-3.6-flash",
        groq_api_key="configured",
        groq_model="openai/gpt-oss-120b",
        openrouter_model="openrouter/free",
    )
    extractor._providers_used = []
    return extractor


def test_model_name_prefers_provider_that_actually_completed_extraction() -> None:
    extractor = _extractor()

    extractor._record_provider(
        "groq:openai/gpt-oss-120b",
        chunk_index=1,
        chunk_count=1,
    )

    assert extractor.model_name == "groq:openai/gpt-oss-120b"


def test_model_name_reports_mixed_provider_analysis() -> None:
    extractor = _extractor()

    extractor._record_provider(
        "gemini:gemini-3.6-flash",
        chunk_index=1,
        chunk_count=3,
    )
    extractor._record_provider(
        "groq:openai/gpt-oss-120b",
        chunk_index=2,
        chunk_count=3,
    )
    extractor._record_provider(
        "groq:openai/gpt-oss-120b",
        chunk_index=3,
        chunk_count=3,
    )

    assert extractor.model_name == "mixed:gemini:gemini-3.6-flash|groq:openai/gpt-oss-120b"
