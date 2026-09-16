from app.services.profile_ai import ProfileAIService


def test_profile_chunk_estimate_is_about_four_thousand_tokens() -> None:
    text = "professional evidence " * 3200
    chunks = ProfileAIService._chunk_fallback_text(text, max_chars=12_000)

    assert len(chunks) > 1
    assert all(ProfileAIService._estimate_tokens(chunk) <= 4_100 for chunk in chunks)


def test_small_profile_text_stays_single_chunk() -> None:
    text = "education and employment evidence " * 200
    chunks = ProfileAIService._chunk_fallback_text(text, max_chars=12_000)

    assert len(chunks) == 1
