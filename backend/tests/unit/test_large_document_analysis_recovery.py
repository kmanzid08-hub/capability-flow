from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.documents import DocumentService
from app.services.profile_ai import ProfileAIService


def test_profile_ai_processing_reference_prefers_current_update_time() -> None:
    document = SimpleNamespace(
        analysis_status="processing",
        updated_at=datetime.now(UTC) - timedelta(minutes=5),
        last_analyzed_at=datetime.now(UTC) - timedelta(days=10),
        created_at=datetime.now(UTC) - timedelta(days=20),
    )

    assert ProfileAIService._is_stale_processing(document) is False


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[object] = []

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, document: object) -> None:
        self.refreshed.append(document)
        document.updated_at = datetime.now(UTC)


@pytest.mark.asyncio
async def test_stale_recovery_refreshes_server_updated_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = SimpleNamespace(
        id=uuid4(),
        person_id=uuid4(),
        analysis_status="processing",
        analysis_error=None,
        updated_at=datetime.now(UTC) - timedelta(minutes=61),
        last_analyzed_at=None,
        created_at=datetime.now(UTC) - timedelta(days=1),
    )
    session = _FakeSession()
    service = object.__new__(DocumentService)
    service.session = session
    service.organization_id = uuid4()

    monkeypatch.setattr(
        "app.services.documents.document_analysis_job_running",
        lambda *_args: False,
    )

    await service._recover_stale_processing([document])

    assert document.analysis_status == "failed"
    assert session.commits == 1
    assert session.refreshed == [document]
