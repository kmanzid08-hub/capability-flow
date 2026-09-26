from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import HTTPException

from app.db.session import AsyncSessionLocal
from app.services.analysis_control import register_analysis_task, unregister_analysis_task
from app.services.profile_ai import ProfileAIService

logger = logging.getLogger(__name__)

DocumentAnalysisKey = tuple[uuid.UUID, uuid.UUID, uuid.UUID]

_jobs: dict[DocumentAnalysisKey, asyncio.Task[None]] = {}


def _key(
    organization_id: uuid.UUID,
    person_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentAnalysisKey:
    return organization_id, person_id, document_id


def document_analysis_job_running(
    organization_id: uuid.UUID,
    person_id: uuid.UUID,
    document_id: uuid.UUID,
) -> bool:
    task = _jobs.get(_key(organization_id, person_id, document_id))
    return task is not None and not task.done()


async def _run_document_analysis_job(
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    person_id: uuid.UUID,
    document_id: uuid.UUID,
) -> None:
    task = asyncio.current_task()
    if task is None:
        return

    register_analysis_task(organization_id, user_id, person_id, task)
    try:
        async with AsyncSessionLocal() as session:
            try:
                await ProfileAIService(
                    session,
                    organization_id,
                    user_id,
                ).analyze_document(
                    person_id,
                    document_id,
                    resume_processing=True,
                )
            except asyncio.CancelledError:
                raise
            except HTTPException as exc:
                logger.warning(
                    "Document analysis background job ended with HTTP %s: "
                    "person_id=%s document_id=%s detail=%s",
                    exc.status_code,
                    person_id,
                    document_id,
                    exc.detail,
                )
            except Exception:
                logger.exception(
                    "Document analysis background job failed: person_id=%s document_id=%s",
                    person_id,
                    document_id,
                )
    finally:
        unregister_analysis_task(organization_id, user_id, person_id, task)


def schedule_document_analysis_job(
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    person_id: uuid.UUID,
    document_id: uuid.UUID,
) -> bool:
    key = _key(organization_id, person_id, document_id)
    existing = _jobs.get(key)
    if existing is not None and not existing.done():
        return False

    task = asyncio.create_task(
        _run_document_analysis_job(
            organization_id=organization_id,
            user_id=user_id,
            person_id=person_id,
            document_id=document_id,
        ),
        name=f"document-analysis-{document_id}",
    )
    _jobs[key] = task

    def _cleanup(done: asyncio.Task[None]) -> None:
        if _jobs.get(key) is done:
            _jobs.pop(key, None)

    task.add_done_callback(_cleanup)
    return True
