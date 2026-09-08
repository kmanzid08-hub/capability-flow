import zipfile
from io import BytesIO

from app.services.document_text import extract_embedded_document_images


def test_extract_embedded_docx_images_prioritizes_supported_larger_media() -> None:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document />")
        archive.writestr("word/media/logo.png", b"x" * 20)
        archive.writestr("word/media/page1.jpg", b"y" * 200)
        archive.writestr("word/media/unsupported.emf", b"z" * 500)

    images = extract_embedded_document_images(
        buffer.getvalue(),
        ".docx",
        max_images=2,
    )

    assert [label for _, _, label in images] == ["page1.jpg", "logo.png"]
    assert [mime for _, mime, _ in images] == ["image/jpeg", "image/png"]


def test_extract_embedded_images_ignores_non_docx_files() -> None:
    assert extract_embedded_document_images(b"not-a-docx", ".pdf", max_images=10) == []
