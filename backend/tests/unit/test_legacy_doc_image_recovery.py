from types import SimpleNamespace

import pytest

from app.services.document_text import extract_embedded_document_images
from app.services.profile_ai import GeminiTemporarilyUnavailable, ProfileAIService

OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _fake_jpeg(payload_size: int) -> bytes:
    return b"\xff\xd8\xff\xe0\x00\x04AB\xff\xda\x00\x02" + (b"A" * payload_size) + b"\xff\xd9"


def test_extract_embedded_images_from_legacy_doc_preserves_document_order() -> None:
    first = _fake_jpeg(5_000)
    second = _fake_jpeg(6_000)
    content = OLE_SIGNATURE + (b"x" * 100) + first + (b"y" * 100) + second

    images = extract_embedded_document_images(content, ".doc", max_images=10)

    assert [label for _, _, label in images] == [
        "legacy-word-image-01.jpg",
        "legacy-word-image-02.jpg",
    ]
    assert [mime for _, mime, _ in images] == ["image/jpeg", "image/jpeg"]
    assert images[0][0] == first
    assert images[1][0] == second


def test_legacy_doc_scan_recovery_is_forced_when_text_layer_is_incomplete() -> None:
    assert ProfileAIService._legacy_word_needs_image_recovery(
        "OFFICIAL DOCUMENTS TRESOR AHADI",
        16,
    )
    assert ProfileAIService._legacy_word_needs_image_recovery("Short typed heading", 1)
    assert not ProfileAIService._legacy_word_needs_image_recovery("A" * 2_000, 1)
    assert not ProfileAIService._legacy_word_needs_image_recovery(None, 0)


@pytest.mark.asyncio
async def test_image_heavy_legacy_doc_refuses_partial_scan_recovery() -> None:
    first = _fake_jpeg(5_000)
    second = _fake_jpeg(6_000)
    content = OLE_SIGNATURE + (b"x" * 100) + first + (b"y" * 100) + second

    class FakeFallbackAI:
        async def extract_image_text(
            self,
            *,
            image_bytes: bytes,
            mime_type: str,
            label: str,
        ) -> tuple[str, str]:
            del image_bytes, mime_type
            if label.endswith("01.jpg"):
                return "Recovered first scanned page", "test:vision"
            return "", "test:vision"

    service = object.__new__(ProfileAIService)
    service.settings = SimpleNamespace(
        ai_docx_vision_max_images=20,
        ai_max_document_chars=500_000,
    )
    service.fallback_ai = FakeFallbackAI()
    document = SimpleNamespace(
        file_extension=".doc",
        original_filename="scanned-packet.doc",
    )

    with pytest.raises(
        GeminiTemporarilyUnavailable,
        match="Analysis was stopped to avoid creating an incomplete profile",
    ):
        await service._recover_image_text(
            document,
            content,
            require_complete=True,
        )
