from app.core.config import Settings
from app.services.profile_ai import ProfileAIService


def test_profile_chunk_size_is_bounded_for_large_documents() -> None:
    settings = Settings(_env_file=None)
    assert settings.ai_profile_chunk_chars == 12_000
    chunks = ProfileAIService._chunk_fallback_text(
        "A" * 30_000,
        max_chars=settings.ai_profile_chunk_chars,
    )
    assert len(chunks) >= 3
    assert all(len(chunk) <= settings.ai_profile_chunk_chars for chunk in chunks)
