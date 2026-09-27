from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.ai_job import AIJob, AIJobStatus, AIJobType
from app.models.document import PersonDocument
from app.models.enums import DocumentAnalysisStatus
from app.models.opportunity import Opportunity, OpportunityAnalysis
from app.models.opportunity_enums import AnalysisStatus, OpportunityStatus
from app.repositories.ai_jobs import AIJobQueueRepository, AIJobRepository


class AIJobQueueFull(RuntimeError):
    pass


@dataclass(frozen=True)
class EnqueuedAIJob:
    job: AIJob
    created: bool


def utc_now() -> datetime:
    return datetime.now(UTC)


class AIJobService:
    """Tenant-scoped AI job admission and cancellation service."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.organization_id = organization_id
        self.user_id = user_id
        self.settings = settings or get_settings()
        self.repo = AIJobRepository(session, organization_id)

    @staticmethod
    def document_key(organization_id: uuid.UUID, document_id: uuid.UUID) -> str:
        return f"document-analysis:{organization_id}:{document_id}"

    @staticmethod
    def opportunity_key(organization_id: uuid.UUID, opportunity_id: uuid.UUID) -> str:
        return f"opportunity-analysis:{organization_id}:{opportunity_id}"

    async def enqueue_document(
        self,
        *,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> EnqueuedAIJob:
        return await self._enqueue(
            job_type=AIJobType.DOCUMENT_ANALYSIS,
            entity_id=document_id,
            person_id=person_id,
            active_key=self.document_key(self.organization_id, document_id),
        )

    async def enqueue_opportunity(
        self,
        *,
        opportunity_id: uuid.UUID,
    ) -> EnqueuedAIJob:
        return await self._enqueue(
            job_type=AIJobType.OPPORTUNITY_ANALYSIS,
            entity_id=opportunity_id,
            person_id=None,
            active_key=self.opportunity_key(self.organization_id, opportunity_id),
        )

    async def _enqueue(
        self,
        *,
        job_type: AIJobType,
        entity_id: uuid.UUID,
        person_id: uuid.UUID | None,
        active_key: str,
    ) -> EnqueuedAIJob:
        existing = await self.repo.active_by_key(active_key)
        if existing is not None:
            return EnqueuedAIJob(existing, False)

        active_count = await self.repo.active_count()
        if active_count >= self.settings.ai_job_max_active_per_organization:
            raise AIJobQueueFull(
                "Your organization's AI queue is currently full. "
                "Existing analyses are still running; please retry shortly."
            )

        job = AIJob(
            organization_id=self.organization_id,
            requested_by_user_id=self.user_id,
            job_type=job_type,
            status=AIJobStatus.QUEUED,
            active_key=active_key,
            entity_id=entity_id,
            person_id=person_id,
            payload={},
            priority=100,
            max_attempts=self.settings.ai_job_max_attempts,
            available_at=utc_now(),
        )
        try:
            # A savepoint contains the uniqueness race without rolling back other
            # request-scoped ORM state already loaded by the route.
            async with self.session.begin_nested():
                self.session.add(job)
                await self.session.flush()
            await self.session.commit()
            await self.session.refresh(job)
            return EnqueuedAIJob(job, True)
        except IntegrityError:
            # Another request may have inserted the same active job between our
            # read and INSERT. Reuse it instead of creating duplicate AI work.
            existing = await self.repo.active_by_key(active_key)
            if existing is None:
                raise
            return EnqueuedAIJob(existing, False)

    async def active_document_ids(
        self,
        document_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        return await self.repo.active_entity_ids(
            AIJobType.DOCUMENT_ANALYSIS,
            document_ids,
        )

    async def cancel_document_jobs(self, person_id: uuid.UUID) -> int:
        jobs = await self.repo.active_for_person(
            AIJobType.DOCUMENT_ANALYSIS,
            person_id,
            requested_by_user_id=self.user_id,
        )
        if not jobs:
            return 0

        now = utc_now()
        cancelled = 0
        for job in jobs:
            if job.status in {AIJobStatus.QUEUED, AIJobStatus.RETRYING}:
                job.status = AIJobStatus.CANCELLED
                job.completed_at = now
                job.active_key = None
                job.worker_id = None
                job.lease_expires_at = None
                job.heartbeat_at = None
            else:
                job.cancel_requested_at = now
            cancelled += 1

        await self.session.commit()
        return cancelled


class AIJobQueueService:
    """System-level queue operations used by worker slots."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = AIJobQueueRepository(session)

    async def claim_next(self, worker_id: str) -> AIJob | None:
        now = utc_now()
        bind = self.session.get_bind()
        if bind.dialect.name == "postgresql":
            # Serialize only the short admission transaction. This prevents two
            # worker processes from both observing the same organization/user
            # concurrency slot as free before either claim commits.
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": 843_479_391},
            )
        candidates = await self.repo.candidates(now)
        changed = False

        for job in candidates:
            if job.cancel_requested_at is not None:
                self._mark_cancelled(job, now)
                changed = True
                continue

            if job.status == AIJobStatus.RUNNING and job.attempt_count >= job.max_attempts:
                await self._mark_failed(
                    job,
                    now,
                    code="lease_expired",
                    message=(
                        "The analysis worker was interrupted repeatedly and the retry "
                        "limit was reached. The saved source is safe and can be analyzed again."
                    ),
                    client_message=(
                        "The analysis was interrupted several times. Your saved source is safe. "
                        "Please start the analysis again."
                    ),
                )
                changed = True
                continue

            org_running = await self.repo.running_count_for_organization(
                job.organization_id,
                now,
                exclude_job_id=job.id,
            )
            if org_running >= self.settings.ai_job_max_concurrent_per_organization:
                continue

            user_running = await self.repo.running_count_for_user(
                job.requested_by_user_id,
                now,
                exclude_job_id=job.id,
            )
            if user_running >= self.settings.ai_job_max_concurrent_per_user:
                continue

            job.status = AIJobStatus.RUNNING
            job.worker_id = worker_id
            job.attempt_count += 1
            job.started_at = job.started_at or now
            job.heartbeat_at = now
            job.lease_expires_at = now + timedelta(seconds=self.settings.ai_job_lease_seconds)
            job.last_error_code = None
            job.last_error_message = None
            await self.session.commit()
            await self.session.refresh(job)
            return job

        if changed:
            await self.session.commit()
        else:
            # Release row locks immediately when every candidate is waiting for
            # an organization/user concurrency slot.
            await self.session.commit()
        return None

    async def heartbeat(self, job_id: uuid.UUID, worker_id: str) -> bool:
        job = await self.repo.get(job_id)
        if job is None or job.status != AIJobStatus.RUNNING or job.worker_id != worker_id:
            return False
        if job.cancel_requested_at is not None:
            return False

        now = utc_now()
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=self.settings.ai_job_lease_seconds)
        await self.session.commit()
        return True

    async def cancel_requested(self, job_id: uuid.UUID, worker_id: str) -> bool:
        job = await self.repo.get(job_id)
        return bool(
            job is not None
            and job.status == AIJobStatus.RUNNING
            and job.worker_id == worker_id
            and job.cancel_requested_at is not None
        )

    async def succeed(
        self,
        job_id: uuid.UUID,
        worker_id: str,
        result: dict[str, object] | None = None,
    ) -> None:
        job = await self.repo.get(job_id)
        if job is None or job.worker_id != worker_id:
            return
        now = utc_now()
        job.status = AIJobStatus.SUCCEEDED
        job.completed_at = now
        job.heartbeat_at = now
        job.lease_expires_at = None
        job.worker_id = None
        job.active_key = None
        job.cancel_requested_at = None
        job.result_json = result
        job.last_error_code = None
        job.last_error_message = None
        await self.session.commit()

    async def cancel(self, job_id: uuid.UUID, worker_id: str) -> None:
        job = await self.repo.get(job_id)
        if job is None or job.worker_id != worker_id:
            return
        self._mark_cancelled(job, utc_now())
        await self.session.commit()

    async def fail_or_retry(
        self,
        job_id: uuid.UUID,
        worker_id: str,
        *,
        code: str,
        message: str,
        retryable: bool,
        client_message: str | None = None,
    ) -> AIJobStatus | None:
        job = await self.repo.get(job_id)
        if job is None or job.worker_id != worker_id:
            return None

        now = utc_now()
        if job.cancel_requested_at is not None:
            self._mark_cancelled(job, now)
            await self.session.commit()
            return AIJobStatus.CANCELLED

        if retryable and job.attempt_count < job.max_attempts:
            delay = min(
                self.settings.ai_job_retry_max_seconds,
                self.settings.ai_job_retry_base_seconds * (2 ** max(job.attempt_count - 1, 0)),
            )
            job.status = AIJobStatus.RETRYING
            job.available_at = now + timedelta(seconds=delay)
            job.heartbeat_at = None
            job.lease_expires_at = None
            job.worker_id = None
            job.last_error_code = code
            job.last_error_message = message
            await self._sync_retrying_target(job)
            await self.session.commit()
            return AIJobStatus.RETRYING

        await self._mark_failed(
            job,
            now,
            code=code,
            message=message,
            client_message=client_message,
        )
        await self.session.commit()
        return AIJobStatus.FAILED

    @staticmethod
    def _mark_cancelled(job: AIJob, now: datetime) -> None:
        job.status = AIJobStatus.CANCELLED
        job.completed_at = now
        job.heartbeat_at = now
        job.lease_expires_at = None
        job.worker_id = None
        job.active_key = None
        job.last_error_code = "cancelled"
        job.last_error_message = "Analysis cancelled by the user."

    async def _sync_retrying_target(self, job: AIJob) -> None:
        retry_message = (
            "A temporary AI service issue occurred. Capability Flow is retrying "
            "the analysis automatically."
        )
        if job.job_type == AIJobType.DOCUMENT_ANALYSIS:
            document = await self.session.get(PersonDocument, job.entity_id)
            if document is not None and document.organization_id == job.organization_id:
                document.analysis_status = DocumentAnalysisStatus.PROCESSING.value
                document.analysis_error = retry_message
            return

        if job.job_type == AIJobType.OPPORTUNITY_ANALYSIS:
            analysis = await self.session.scalar(
                select(OpportunityAnalysis)
                .where(
                    OpportunityAnalysis.organization_id == job.organization_id,
                    OpportunityAnalysis.opportunity_id == job.entity_id,
                )
                .order_by(OpportunityAnalysis.version.desc())
                .limit(1)
            )
            if analysis is not None and analysis.status == AnalysisStatus.FAILED:
                analysis.status = AnalysisStatus.ANALYZING
                analysis.error_message = retry_message
                analysis.completed_at = None

            opportunity = await self.session.get(Opportunity, job.entity_id)
            if (
                opportunity is not None
                and opportunity.organization_id == job.organization_id
                and opportunity.status == OpportunityStatus.NEEDS_REVIEW
            ):
                opportunity.status = OpportunityStatus.ANALYZING

    async def _mark_failed(
        self,
        job: AIJob,
        now: datetime,
        *,
        code: str,
        message: str,
        client_message: str | None = None,
    ) -> None:
        job.status = AIJobStatus.FAILED
        job.completed_at = now
        job.heartbeat_at = now
        job.lease_expires_at = None
        job.worker_id = None
        job.active_key = None
        job.last_error_code = code
        job.last_error_message = message

        safe_message = client_message or (
            "We could not complete this analysis after several automatic retries. "
            "Your saved source is safe. Please try again shortly."
        )

        if job.job_type == AIJobType.DOCUMENT_ANALYSIS:
            document = await self.session.get(PersonDocument, job.entity_id)
            if document is not None and document.organization_id == job.organization_id:
                document.analysis_status = DocumentAnalysisStatus.FAILED.value
                document.analysis_error = safe_message
                document.last_analyzed_at = now
            return

        if job.job_type == AIJobType.OPPORTUNITY_ANALYSIS:
            analysis = await self.session.scalar(
                select(OpportunityAnalysis)
                .where(
                    OpportunityAnalysis.organization_id == job.organization_id,
                    OpportunityAnalysis.opportunity_id == job.entity_id,
                )
                .order_by(OpportunityAnalysis.version.desc())
                .limit(1)
            )
            if analysis is not None and analysis.status in {
                AnalysisStatus.ANALYZING,
                AnalysisStatus.MATCHING,
                AnalysisStatus.BUILDING_TEAM,
            }:
                analysis.status = AnalysisStatus.FAILED
                analysis.error_message = safe_message
                analysis.completed_at = now

            opportunity = await self.session.get(Opportunity, job.entity_id)
            if (
                opportunity is not None
                and opportunity.organization_id == job.organization_id
                and opportunity.status == OpportunityStatus.ANALYZING
            ):
                opportunity.status = OpportunityStatus.NEEDS_REVIEW
