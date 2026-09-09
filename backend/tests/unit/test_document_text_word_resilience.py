# ruff: noqa: E501

import zipfile
from io import BytesIO

from app.services.document_text import (
    detect_word_content_type,
    extract_embedded_document_images,
    extract_text,
)


def _minimal_word_package(*, body_text: str = "", image: bytes | None = None) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
              <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
              <Default Extension="xml" ContentType="application/xml"/>
              <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
            </Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
            </Relationships>""",
        )
        archive.writestr(
            "word/document.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>{body_text}</w:t></w:r></w:p></w:body>
            </w:document>""",
        )
        if image is not None:
            archive.writestr("word/media/page1.jpg", image)
    return buffer.getvalue()


def test_mislabeled_doc_ooxml_is_detected_and_read() -> None:
    content = _minimal_word_package(body_text="Senior consultant with project experience")

    assert detect_word_content_type(content, ".doc") == ".docx"
    assert "Senior consultant" in extract_text(content, ".doc", 10000)


def test_direct_word_xml_recovery_handles_minimal_package() -> None:
    content = _minimal_word_package(body_text="Recovered directly from document XML")

    text = extract_text(content, ".docx", 10000)

    assert "Recovered directly from document XML" in text


def test_mislabeled_rtf_doc_is_read_automatically() -> None:
    content = b"{\\rtf1\\ansi Professional profile\\par Project manager with ten years experience}"

    assert detect_word_content_type(content, ".doc") == ".rtf"
    text = extract_text(content, ".doc", 10000)
    assert "Professional profile" in text
    assert "Project manager" in text


def test_ooxml_images_are_recovered_even_when_file_is_named_doc() -> None:
    content = _minimal_word_package(image=b"x" * 200)

    images = extract_embedded_document_images(content, ".doc", max_images=3)

    assert len(images) == 1
    assert images[0][1] == "image/jpeg"
    assert images[0][2] == "page1.jpg"
