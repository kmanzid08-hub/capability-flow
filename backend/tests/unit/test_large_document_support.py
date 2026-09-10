from io import BytesIO
from types import SimpleNamespace

from app.services.document_storage import R2DocumentStorage
from app.services.requirement_extraction import GeminiRequirementExtractor


def test_r2_stream_size_does_not_consume_upload() -> None:
    stream = BytesIO(b"x" * 4096)
    stream.seek(321)

    assert R2DocumentStorage._stream_size(stream) == 4096
    assert stream.tell() == 321


def test_opportunity_chunking_preserves_document_tail() -> None:
    extractor = object.__new__(GeminiRequirementExtractor)
    extractor.opportunity_settings = SimpleNamespace(
        opportunity_analysis_chunk_characters=20_000,
        opportunity_analysis_chunk_overlap=1_000,
    )
    text = ("A" * 24_000) + "\nTAIL-MANDATORY-REQUIREMENT"

    chunks = extractor._chunk_source(text)

    assert len(chunks) >= 2
    assert chunks[-1].endswith("TAIL-MANDATORY-REQUIREMENT")
