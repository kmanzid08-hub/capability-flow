from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.opportunity_enums import AnalysisStatus, OpportunityStatus
from app.services import opportunities as opportunities_module
from app.services.opportunities import OpportunityService


@pytest.mark.asyncio
async def test_stale_recovery_preserves_analysis_while_durable_job_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analysis = SimpleNamespace(
        status=AnalysisStatus.ANALYZING,
        started_at=datetime.now(UTC) - timedelta(minutes=31),
        error_message=None,
        completed_at=None,
    )
    opportunity = SimpleNamespace(status=OpportunityStatus.ANALYZING)

    service = object.__new__(OpportunityService)
    service.organization_id = uuid4()
    service.user_id = uuid4()
    service.repo = SimpleNamespace(latest_analysis=AsyncMock(return_value=analysis))
    service.session = SimpleNamespace(commit=AsyncMock())
    service.get = AsyncMock(return_value=opportunity)

    active_jobs = SimpleNamespace(opportunity_job_active=AsyncMock(return_value=True))
    monkeypatch.setattr(
        opportunities_module,
        "AIJobService",
        lambda *_args, **_kwargs: active_jobs,
    )

    await service._recover_stale_analysis(uuid4())

    assert analysis.status == AnalysisStatus.ANALYZING
    assert analysis.error_message is None
    assert analysis.completed_at is None
    service.get.assert_not_awaited()
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_explicit_retry_recovery_can_supersede_active_job_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analysis = SimpleNamespace(
        status=AnalysisStatus.ANALYZING,
        started_at=datetime.now(UTC) - timedelta(minutes=1),
        error_message=None,
        completed_at=None,
    )
    opportunity = SimpleNamespace(status=OpportunityStatus.ANALYZING)

    service = object.__new__(OpportunityService)
    service.organization_id = uuid4()
    service.user_id = uuid4()
    service.repo = SimpleNamespace(latest_analysis=AsyncMock(return_value=analysis))
    service.session = SimpleNamespace(commit=AsyncMock())
    service.get = AsyncMock(return_value=opportunity)

    class UnexpectedAIJobService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("active-job lookup must be bypassed for explicit retry recovery")

    monkeypatch.setattr(opportunities_module, "AIJobService", UnexpectedAIJobService)

    await service._recover_stale_analysis(
        uuid4(),
        max_age=timedelta(seconds=0),
        respect_active_job=False,
    )

    assert analysis.status == AnalysisStatus.FAILED
    assert "remained active for more than 0 minutes" in analysis.error_message
    assert analysis.completed_at is not None
    assert opportunity.status == OpportunityStatus.NEEDS_REVIEW
    service.session.commit.assert_awaited_once()
