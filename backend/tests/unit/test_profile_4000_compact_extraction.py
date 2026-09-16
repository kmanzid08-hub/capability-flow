from app.services.profile_ai import AIProfileChunkExtraction, ProfileAIService


def test_profile_chunks_are_bounded_to_safe_input_size() -> None:
    text = "professional evidence " * 3200
    chunks = ProfileAIService._chunk_fallback_text(text, max_chars=12_000)
    assert len(chunks) > 1
    assert all(ProfileAIService._estimate_tokens(chunk) <= 4_000 for chunk in chunks)


def test_compact_chunk_schema_is_available() -> None:
    schema = AIProfileChunkExtraction.model_json_schema()
    assert "skills" in schema["properties"]
    assert "employment" in schema["properties"]
    assert "projects" in schema["properties"]


def test_small_profile_text_stays_single_chunk() -> None:
    text = "education and employment evidence " * 200
    chunks = ProfileAIService._chunk_fallback_text(text, max_chars=12_000)
    assert len(chunks) == 1
