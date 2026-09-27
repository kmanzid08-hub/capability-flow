from __future__ import annotations

import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_job import ACTIVE_AI_JOB_STATUSES, AIJob, AIJobStatus, AIJobType


class AIJobRepository:
    """Tenant-scoped persistence for AI jobs created by API requests."""

    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    def _scoped(self) -> Select[tuple[AIJob]]:
        return select(AIJob).where(AIJob.organization_id == self.organization_id)

    async def active_by_key(self, active_key: str) -> AIJob | None:
        return cast(
            AIJob | None,
            await self.session.scalar(
                self._scoped().where(
                    AIJob.active_key == active_key,
                    AIJob.status.in_(ACTIVE_AI_JOB_STATUSES),
                )
            ),
        )

    async def active_count(self) -> int:
        value = await self.session.scalar(
            select(func.count())
            .select_from(AIJob)
            .where(
                AIJob.organization_id == self.organization_id,
                AIJob.status.in_(ACTIVE_AI_JOB_STATUSES),
            )
        )
        return int(value or 0)

    async def active_entity_ids(
        self,
        job_type: AIJobType,
        entity_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        if not entity_ids:
            return set()
        rows = await self.session.scalars(
            self._scoped().where(
                AIJob.job_type == job_type,
                AIJob.entity_id.in_(entity_ids),
                AIJob.status.in_(ACTIVE_AI_JOB_STATUSES),
            )
        )
        return {job.entity_id for job in rows}

    async def active_for_entity(
        self,
        job_type: AIJobType,
        entity_id: uuid.UUID,
    ) -> AIJob | None:
        return cast(
            AIJob | None,
            await self.session.scalar(
                self._scoped()
                .where(
                    AIJob.job_type == job_type,
                    AIJob.entity_id == entity_id,
                    AIJob.status.in_(ACTIVE_AI_JOB_STATUSES),
                )
                .order_by(AIJob.created_at.desc())
                .limit(1)
            ),
        )

    async def active_for_person(
        self,
        job_type: AIJobType,
        person_id: uuid.UUID,
        requested_by_user_id: uuid.UUID | None = None,
    ) -> list[AIJob]:
        query = self._scoped().where(
            AIJob.job_type == job_type,
            AIJob.person_id == person_id,
            AIJob.status.in_(ACTIVE_AI_JOB_STATUSES),
        )
        if requested_by_user_id is not None:
            query = query.where(AIJob.requested_by_user_id == requested_by_user_id)
        return list(await self.session.scalars(query))


class AIJobQueueRepository:
    """System queue persistence used only by the internal worker."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def candidates(self, now: datetime, limit: int = 25) -> list[AIJob]:
        query = (
            select(AIJob)
            .where(
                AIJob.status.in_(
                    {
                        AIJobStatus.QUEUED,
                        AIJobStatus.RETRYING,
                        AIJobStatus.RUNNING,
                    }
                ),
                ((AIJob.status != AIJobStatus.RUNNING) & (AIJob.available_at <= now))
                | (
                    (AIJob.status == AIJobStatus.RUNNING)
                    & (AIJob.lease_expires_at.is_not(None))
                    & (AIJob.lease_expires_at <= now)
                ),
            )
            .order_by(AIJob.priority.asc(), AIJob.available_at.asc(), AIJob.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(await self.session.scalars(query))

    async def running_count_for_organization(
        self,
        organization_id: uuid.UUID,
        now: datetime,
        *,
        exclude_job_id: uuid.UUID | None = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(AIJob)
            .where(
                AIJob.organization_id == organization_id,
                AIJob.status == AIJobStatus.RUNNING,
                AIJob.lease_expires_at.is_not(None),
                AIJob.lease_expires_at > now,
            )
        )
        if exclude_job_id is not None:
            query = query.where(AIJob.id != exclude_job_id)
        value = await self.session.scalar(query)
        return int(value or 0)

    async def running_count_for_user(
        self,
        user_id: uuid.UUID,
        now: datetime,
        *,
        exclude_job_id: uuid.UUID | None = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(AIJob)
            .where(
                AIJob.requested_by_user_id == user_id,
                AIJob.status == AIJobStatus.RUNNING,
                AIJob.lease_expires_at.is_not(None),
                AIJob.lease_expires_at > now,
            )
        )
        if exclude_job_id is not None:
            query = query.where(AIJob.id != exclude_job_id)
        value = await self.session.scalar(query)
        return int(value or 0)

    async def get(self, job_id: uuid.UUID) -> AIJob | None:
        return await self.session.get(AIJob, job_id)
