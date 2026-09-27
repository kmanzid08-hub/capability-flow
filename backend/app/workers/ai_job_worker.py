from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid

from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.db.session import AsyncSessionLocal
from app.models.ai_job import AIJob, AIJobStatus, AIJobType
from app.services.ai_jobs import AIJobQueueService
from app.services.analysis_control import register_analysis_task, unregister_analysis_task
from app.services.opportunities import OpportunityService
from app.services.profile_ai import ProfileAIService

logger = logging.getLogger(__name__)


class AIJobWorker:
    """Durable PostgreSQL-backed AI job worker.

    The worker runs inside the API service for now so it shares the existing
    document storage mount. The queue itself is durable, so a Render restart
    only interrupts the lease; a new process reclaims the job automatically.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        identity = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self.worker_id = identity
        self._stop = asyncio.Event()
        self._slots: list[asyncio.Task[None]] = []
        self._running_jobs: dict[uuid.UUID, asyncio.Task[dict[str, object]]] = {}

    async def start(self) -> None:
        if self._slots:
            return
        self._stop.clear()
        for slot in range(self.settings.ai_job_worker_concurrency):
            task = asyncio.create_task(
                self._run_slot(slot),
                name=f"ai-job-worker-{slot}",
            )
            self._slots.append(task)
        logger.info(
            "AI job worker started: worker_id=%s concurrency=%s",
            self.worker_id,
            self.settings.ai_job_worker_concurrency,
        )

    async def stop(self) -> None:
        self._stop.set()
        slots = list(self._slots)
        self._slots.clear()
        for task in slots:
            task.cancel()
        if slots:
            await asyncio.gather(*slots, return_exceptions=True)
        logger.info(
            "AI job worker stopped claiming new work: worker_id=%s active_jobs=%s",
            self.worker_id,
            len(self._running_jobs),
        )

    async def _run_slot(self, slot: int) -> None:
        while not self._stop.is_set():
            try:
                job = await self._claim_next()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "AI worker could not claim work: worker_id=%s slot=%s",
                    self.worker_id,
                    slot,
                )
                await asyncio.sleep(min(self.settings.ai_job_poll_seconds * 5, 10.0))
                continue

            if job is None:
                try:
                    await asyncio.wait_for(
                        self._stop.wait(),
                        timeout=self.settings.ai_job_poll_seconds,
                    )
                except TimeoutError:
                    pass
                continue

            logger.info(
                "AI job claimed: worker_id=%s slot=%s job_id=%s type=%s attempt=%s/%s org=%s",
                self.worker_id,
                slot,
                job.id,
                job.job_type.value,
                job.attempt_count,
                job.max_attempts,
                job.organization_id,
            )
            execution = asyncio.create_task(
                self._execute(job),
                name=f"ai-job-{job.id}",
            )
            self._running_jobs[job.id] = execution
            try:
                # Shield the durable job from supervisor cancellation during a
                # graceful web-service restart. If the process is terminated,
                # the database lease expires and another process resumes it.
                await asyncio.shield(execution)
            except asyncio.CancelledError:
                if self._stop.is_set():
                    return
                raise
            except Exception:
                # A secondary failure while persisting retry/terminal state must
                # not permanently kill this worker slot. The lease remains the
                # final recovery mechanism if the database was temporarily down.
                logger.exception(
                    "AI worker execution wrapper failed: worker_id=%s slot=%s job_id=%s",
                    self.worker_id,
                    slot,
                    job.id,
                )
            finally:
                if execution.done():
                    self._running_jobs.pop(job.id, None)

    async def _claim_next(self) -> AIJob | None:
        async with AsyncSessionLocal() as session:
            return await AIJobQueueService(session, self.settings).claim_next(self.worker_id)

    async def _execute(self, job: AIJob) -> dict[str, object]:
        domain_task = asyncio.create_task(
            self._dispatch(job),
            name=f"ai-job-domain-{job.id}",
        )
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(job.id, domain_task),
            name=f"ai-job-heartbeat-{job.id}",
        )

        try:
            result = await domain_task
        except asyncio.CancelledError:
            if await self._is_cancel_requested(job.id):
                await self._mark_cancelled(job.id)
                logger.info("AI job cancelled by user: job_id=%s", job.id)
                return {"status": "cancelled"}
            await self._handle_failure(
                job,
                code="unexpected_cancellation",
                message=(
                    "The analysis task was interrupted unexpectedly. "
                    "It has been returned to the durable retry queue."
                ),
                retryable=True,
            )
            return {"status": "retrying"}
        except HTTPException as exc:
            await self._handle_failure(
                job,
                code=f"http_{exc.status_code}",
                message=str(exc.detail),
                retryable=exc.status_code in {408, 409, 429, 500, 502, 503, 504},
                client_message=str(exc.detail),
            )
            return {"status": "failed"}
        except Exception as exc:
            logger.exception("AI job execution failed: job_id=%s type=%s", job.id, job.job_type)
            await self._handle_failure(
                job,
                code=type(exc).__name__,
                message=str(exc) or "Unexpected AI job failure",
                retryable=True,
            )
            return {"status": "failed"}
        finally:
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)

        async with AsyncSessionLocal() as session:
            await AIJobQueueService(session, self.settings).succeed(
                job.id,
                self.worker_id,
                result,
            )
        logger.info("AI job completed: job_id=%s type=%s", job.id, job.job_type.value)
        return result

    async def _dispatch(self, job: AIJob) -> dict[str, object]:
        if job.job_type == AIJobType.DOCUMENT_ANALYSIS:
            if job.person_id is None:
                raise RuntimeError("Document analysis job is missing person_id")
            task = asyncio.current_task()
            if task is None:
                raise RuntimeError("Document analysis worker task is unavailable")

            register_analysis_task(
                job.organization_id,
                job.requested_by_user_id,
                job.person_id,
                task,
            )
            try:
                async with AsyncSessionLocal() as session:
                    count = await ProfileAIService(
                        session,
                        job.organization_id,
                        job.requested_by_user_id,
                    ).analyze_document(
                        job.person_id,
                        job.entity_id,
                        resume_processing=True,
                    )
                return {
                    "document_id": str(job.entity_id),
                    "suggestions_created": count,
                }
            finally:
                unregister_analysis_task(
                    job.organization_id,
                    job.requested_by_user_id,
                    job.person_id,
                    task,
                )

        if job.job_type == AIJobType.OPPORTUNITY_ANALYSIS:
            async with AsyncSessionLocal() as session:
                analysis = await OpportunityService(
                    session,
                    job.organization_id,
                    job.requested_by_user_id,
                ).analyze(
                    job.entity_id,
                    resume_interrupted=True,
                )
            return {
                "opportunity_id": str(job.entity_id),
                "analysis_id": str(analysis.id),
                "analysis_version": analysis.version,
                "analysis_status": analysis.status.value,
            }

        raise RuntimeError(f"Unsupported AI job type: {job.job_type}")

    async def _heartbeat_loop(
        self,
        job_id: uuid.UUID,
        domain_task: asyncio.Task[dict[str, object]],
    ) -> None:
        while not domain_task.done():
            await asyncio.sleep(self.settings.ai_job_heartbeat_seconds)
            try:
                async with AsyncSessionLocal() as session:
                    keep_running = await AIJobQueueService(session, self.settings).heartbeat(
                        job_id,
                        self.worker_id,
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "AI job heartbeat failed temporarily: worker_id=%s job_id=%s",
                    self.worker_id,
                    job_id,
                )
                continue
            if not keep_running:
                if not domain_task.done():
                    domain_task.cancel()
                return

    async def _is_cancel_requested(self, job_id: uuid.UUID) -> bool:
        async with AsyncSessionLocal() as session:
            return await AIJobQueueService(session, self.settings).cancel_requested(
                job_id,
                self.worker_id,
            )

    async def _mark_cancelled(self, job_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            await AIJobQueueService(session, self.settings).cancel(job_id, self.worker_id)

    async def _handle_failure(
        self,
        job: AIJob,
        *,
        code: str,
        message: str,
        retryable: bool,
        client_message: str | None = None,
    ) -> None:
        async with AsyncSessionLocal() as session:
            status = await AIJobQueueService(session, self.settings).fail_or_retry(
                job.id,
                self.worker_id,
                code=code,
                message=message[:4000],
                retryable=retryable,
                client_message=client_message,
            )
        if status == AIJobStatus.RETRYING:
            logger.warning(
                "AI job scheduled for retry: job_id=%s attempt=%s/%s code=%s",
                job.id,
                job.attempt_count,
                job.max_attempts,
                code,
            )
        elif status == AIJobStatus.CANCELLED:
            logger.info("AI job cancelled while handling failure: job_id=%s", job.id)
        else:
            logger.error(
                "AI job permanently failed: job_id=%s attempt=%s/%s code=%s",
                job.id,
                job.attempt_count,
                job.max_attempts,
                code,
            )


async def run_worker_forever() -> None:
    """Optional standalone worker entrypoint for a future dedicated service."""
    worker = AIJobWorker()
    await worker.start()
    try:
        await asyncio.Event().wait()
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(run_worker_forever())
