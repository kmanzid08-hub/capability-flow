from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai_job import AIJobStatus
from app.models.organization import Organization
from app.models.person import Person
from app.models.user import User
from app.repositories.ai_jobs import AIJobRepository
from app.services.ai_jobs import AIJobQueueService, AIJobService


async def _entities(session: AsyncSession, suffix: str) -> tuple[Organization, User, Person]:
    organization = Organization(name=f"Org {suffix}", slug=f"org-{suffix}")
    user = User(
        email=f"{suffix}@example.com",
        password_hash="hash",
        full_name=f"User {suffix}",
    )
    session.add_all([organization, user])
    await session.flush()
    person = Person(
        organization_id=organization.id,
        first_name="Amina",
        last_name="Kamanzi",
        display_name="Amina Kamanzi",
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    session.add(person)
    await session.commit()
    return organization, user, person


@pytest.mark.asyncio
async def test_enqueue_deduplicates_active_document_job(session: AsyncSession) -> None:
    organization, user, person = await _entities(session, uuid4().hex[:8])
    document_id = uuid4()
    service = AIJobService(session, organization.id, user.id)

    first = await service.enqueue_document(person_id=person.id, document_id=document_id)
    second = await service.enqueue_document(person_id=person.id, document_id=document_id)

    assert first.created is True
    assert second.created is False
    assert second.job.id == first.job.id
    assert first.job.status == AIJobStatus.QUEUED


@pytest.mark.asyncio
async def test_ai_job_repository_is_tenant_scoped(session: AsyncSession) -> None:
    first_org, first_user, first_person = await _entities(session, uuid4().hex[:8])
    second_org, _second_user, _second_person = await _entities(session, uuid4().hex[:8])
    document_id = uuid4()

    enqueued = await AIJobService(session, first_org.id, first_user.id).enqueue_document(
        person_id=first_person.id,
        document_id=document_id,
    )

    visible_to_first = await AIJobRepository(session, first_org.id).active_entity_ids(
        enqueued.job.job_type,
        [document_id],
    )
    visible_to_second = await AIJobRepository(session, second_org.id).active_entity_ids(
        enqueued.job.job_type,
        [document_id],
    )

    assert visible_to_first == {document_id}
    assert visible_to_second == set()


@pytest.mark.asyncio
async def test_worker_claim_respects_per_user_concurrency(session: AsyncSession) -> None:
    settings = get_settings()
    original_org = settings.ai_job_max_concurrent_per_organization
    original_user = settings.ai_job_max_concurrent_per_user
    settings.ai_job_max_concurrent_per_organization = 1
    settings.ai_job_max_concurrent_per_user = 1
    try:
        organization, user, person = await _entities(session, uuid4().hex[:8])
        service = AIJobService(session, organization.id, user.id, settings)
        first = await service.enqueue_document(person_id=person.id, document_id=uuid4())
        second = await service.enqueue_document(person_id=person.id, document_id=uuid4())
        first_id = first.job.id
        second_id = second.job.id

        queue = AIJobQueueService(session, settings)
        claimed_first = await queue.claim_next("worker-a")
        claimed_second = await queue.claim_next("worker-b")

        assert claimed_first is not None
        assert claimed_first.id == first_id
        assert claimed_second is None

        await queue.succeed(claimed_first.id, "worker-a", {"ok": True})
        claimed_second = await queue.claim_next("worker-b")
        assert claimed_second is not None
        assert claimed_second.id == second_id
    finally:
        settings.ai_job_max_concurrent_per_organization = original_org
        settings.ai_job_max_concurrent_per_user = original_user


@pytest.mark.asyncio
async def test_expired_lease_is_reclaimed(session: AsyncSession) -> None:
    settings = get_settings()
    organization, user, person = await _entities(session, uuid4().hex[:8])
    service = AIJobService(session, organization.id, user.id, settings)
    enqueued = await service.enqueue_document(person_id=person.id, document_id=uuid4())

    queue = AIJobQueueService(session, settings)
    claimed = await queue.claim_next("worker-a")
    assert claimed is not None
    assert claimed.attempt_count == 1

    claimed.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await session.commit()

    reclaimed = await queue.claim_next("worker-b")
    assert reclaimed is not None
    assert reclaimed.id == enqueued.job.id
    assert reclaimed.worker_id == "worker-b"
    assert reclaimed.attempt_count == 2


@pytest.mark.asyncio
async def test_cancel_queued_document_job_is_durable(session: AsyncSession) -> None:
    organization, user, person = await _entities(session, uuid4().hex[:8])
    service = AIJobService(session, organization.id, user.id)
    enqueued = await service.enqueue_document(person_id=person.id, document_id=uuid4())

    cancelled = await service.cancel_document_jobs(person.id)
    await session.refresh(enqueued.job)

    assert cancelled == 1
    assert enqueued.job.status == AIJobStatus.CANCELLED
    assert enqueued.job.active_key is None


@pytest.mark.asyncio
async def test_opportunity_retry_waits_for_provider_quota_recovery(
    session: AsyncSession,
) -> None:
    from app.core.config import Settings
    from app.models.opportunity import Opportunity
    from app.services.ai_provider_health import (
        get_provider_health,
        reset_provider_health_for_tests,
    )
    class QuotaError(RuntimeError):
        status_code = 429

    organization, user, _ = await _entities(session, uuid4().hex[:8])
    opportunity = Opportunity(
        organization_id=organization.id,
        title="Multi-section consultancy TOR",
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    session.add(opportunity)
    await session.commit()
    settings = Settings(
        _env_file=None,
        gemini_api_key="quota-recovery-test",
        groq_api_key=None,
        openrouter_api_key=None,
        openai_api_key=None,
    )
    service = AIJobService(session, organization.id, user.id, settings)
    await service.enqueue_opportunity(opportunity_id=opportunity.id)
    queue = AIJobQueueService(session, settings)
    claimed = await queue.claim_next("worker-quota")
    assert claimed is not None
    reset_provider_health_for_tests()
    try:
        get_provider_health().record_failure(
            "gemini",
            QuotaError("GenerateRequestsPerDayPerProjectPerModel daily quota"),
        )
        result = await queue.fail_or_retry(
            claimed.id,
            "worker-quota",
            code="http_503",
            message="All configured AI providers are currently unavailable.",
            retryable=True,
        )
        assert result == AIJobStatus.RETRYING
        seconds_until_retry = (
            claimed.available_at.replace(tzinfo=UTC) - datetime.now(UTC)
        ).total_seconds()
        assert seconds_until_retry > 3_500
    finally:
        reset_provider_health_for_tests()
