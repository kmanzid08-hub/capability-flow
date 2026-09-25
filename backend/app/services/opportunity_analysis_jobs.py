from __future__ import annotations

import asyncio
import logging
import uuid

from app.db.session import AsyncSessionLocal
from app.services.opportunities import OpportunityService

logger = logging.getLogger(__name__)

_running_jobs: dict[uuid.UUID, asyncio.Task[None]] = {}


def opportunity_analysis_job_running(opportunity_id: uuid.UUID) -> bool:
    task = _running_jobs.get(opportunity_id)
    return task is not None and not task.done()


def schedule_opportunity_analysis_job(
    opportunity_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    if opportunity_analysis_job_running(opportunity_id):
        return False

    task = asyncio.create_task(
        run_opportunity_analysis_job(
            opportunity_id,
            organization_id,
            user_id,
        )
    )
    _running_jobs[opportunity_id] = task

    def cleanup(done_task: asyncio.Task[None]) -> None:
        if _running_jobs.get(opportunity_id) is done_task:
            _running_jobs.pop(opportunity_id, None)

    task.add_done_callback(cleanup)
    return True


async def run_opportunity_analysis_job(
    opportunity_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Run long opportunity analysis outside the browser request lifecycle."""
    try:
        async with AsyncSessionLocal() as session:
            try:
                await OpportunityService(
                    session,
                    organization_id,
                    user_id,
                ).analyze(opportunity_id)
            except Exception:
                # OpportunityService.analyze persists FAILED when it can.
                logger.exception(
                    "Opportunity analysis background job failed: opportunity=%s",
                    opportunity_id,
                )
    except asyncio.CancelledError:
        logger.warning(
            "Opportunity analysis interrupted by process shutdown: opportunity=%s",
            opportunity_id,
        )
        raise
