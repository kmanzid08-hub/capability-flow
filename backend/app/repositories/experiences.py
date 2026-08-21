import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import (
    EmploymentExperience,
    ProjectExperience,
)


class EmploymentRepository:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id

    async def list(
        self,
        person_id: uuid.UUID,
    ) -> list[EmploymentExperience]:
        result = await self.session.scalars(
            select(EmploymentExperience)
            .where(
                EmploymentExperience.organization_id == self.organization_id,
                EmploymentExperience.person_id == person_id,
            )
            .order_by(
                EmploymentExperience.is_current.desc(),
                EmploymentExperience.start_date.desc(),
            )
        )

        return list(result)

    async def get(
        self,
        person_id: uuid.UUID,
        experience_id: uuid.UUID,
    ) -> EmploymentExperience | None:
        result = await self.session.scalars(
            select(EmploymentExperience).where(
                EmploymentExperience.id == experience_id,
                EmploymentExperience.person_id == person_id,
                EmploymentExperience.organization_id == self.organization_id,
            )
        )

        return result.first()

    def add(
        self,
        experience: EmploymentExperience,
    ) -> None:
        if experience.organization_id != self.organization_id:
            raise ValueError("Employment organization does not match repository context")

        self.session.add(experience)


class ProjectRepository:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id

    async def list(
        self,
        person_id: uuid.UUID,
    ) -> list[ProjectExperience]:
        result = await self.session.scalars(
            select(ProjectExperience)
            .where(
                ProjectExperience.organization_id == self.organization_id,
                ProjectExperience.person_id == person_id,
            )
            .order_by(
                ProjectExperience.is_current.desc(),
                ProjectExperience.start_date.desc(),
            )
        )

        return list(result)

    async def get(
        self,
        person_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> ProjectExperience | None:
        result = await self.session.scalars(
            select(ProjectExperience).where(
                ProjectExperience.id == project_id,
                ProjectExperience.person_id == person_id,
                ProjectExperience.organization_id == self.organization_id,
            )
        )

        return result.first()

    def add(
        self,
        project: ProjectExperience,
    ) -> None:
        if project.organization_id != self.organization_id:
            raise ValueError("Project organization does not match repository context")

        self.session.add(project)
