from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.documents import DocumentService


def test_stale_processing_document_is_detected() -> None:
    document = SimpleNamespace(
        analysis_status="processing",
        last_analyzed_at=datetime.now(UTC) - timedelta(minutes=31),
        created_at=datetime.now(UTC) - timedelta(days=1),
    )

    assert DocumentService._is_stale_processing(document) is True


def test_recent_processing_document_is_not_stale() -> None:
    document = SimpleNamespace(
        analysis_status="processing",
        last_analyzed_at=datetime.now(UTC) - timedelta(minutes=5),
        created_at=datetime.now(UTC) - timedelta(days=1),
    )

    assert DocumentService._is_stale_processing(document) is False
