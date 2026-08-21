import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import (
    EmploymentExperience,
    ProjectExperience,
)
from app.repositories.experiences import (
    EmploymentRepository,
    ProjectRepository,
)
from app.repositories.people import PersonRepository
from app.schemas.experience import (
    EmploymentCreate,
    EmploymentUpdate,
    ProjectCreate,
    ProjectUpdate,
)


class ExperienceService:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id

        self.people = PersonRepository(
            session,
            organization_id,
        )

        self.employment = EmploymentRepository(
            session,
            organization_id,
        )

        self.projects = ProjectRepository(
            session,
            organization_id,
        )

    async def ensure_person(
        self,
        person_id: uuid.UUID,
    ) -> None:
        person = await self.people.get(person_id)

        if person is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person not found",
            )

    @staticmethod
    def validate_dates(
        *,
        start_date: date,
        end_date: date | None,
        is_current: bool,
        current_label: str,
    ) -> None:
        if is_current and end_date is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(f"Current {current_label} cannot have an end date"),
            )

        if end_date is not None and end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="End date cannot be earlier than start date",
            )

    async def list_employment(
        self,
        person_id: uuid.UUID,
    ) -> list[EmploymentExperience]:
        await self.ensure_person(person_id)
        return await self.employment.list(person_id)

    async def create_employment(
        self,
        person_id: uuid.UUID,
        data: EmploymentCreate,
    ) -> EmploymentExperience:
        await self.ensure_person(person_id)

        values = data.model_dump()

        experience = EmploymentExperience(
            **values,
            organization_id=self.organization_id,
            person_id=person_id,
        )

        self.employment.add(experience)

        await self.session.commit()
        await self.session.refresh(experience)

        return experience

    async def update_employment(
        self,
        person_id: uuid.UUID,
        experience_id: uuid.UUID,
        data: EmploymentUpdate,
    ) -> EmploymentExperience:
        await self.ensure_person(person_id)

        experience = await self.employment.get(
            person_id,
            experience_id,
        )

        if experience is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employment experience not found",
            )

        values = data.model_dump(exclude_unset=True)

        new_start_date = values.get(
            "start_date",
            experience.start_date,
        )

        new_end_date = values.get(
            "end_date",
            experience.end_date,
        )

        new_is_current = values.get(
            "is_current",
            experience.is_current,
        )

        self.validate_dates(
            start_date=new_start_date,
            end_date=new_end_date,
            is_current=new_is_current,
            current_label="employment",
        )

        for field, value in values.items():
            setattr(experience, field, value)

        await self.session.commit()
        await self.session.refresh(experience)

        return experience

    async def delete_employment(
        self,
        person_id: uuid.UUID,
        experience_id: uuid.UUID,
    ) -> None:
        await self.ensure_person(person_id)

        experience = await self.employment.get(
            person_id,
            experience_id,
        )

        if experience is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employment experience not found",
            )

        await self.session.delete(experience)
        await self.session.commit()

    async def list_projects(
        self,
        person_id: uuid.UUID,
    ) -> list[ProjectExperience]:
        await self.ensure_person(person_id)
        return await self.projects.list(person_id)

    async def create_project(
        self,
        person_id: uuid.UUID,
        data: ProjectCreate,
    ) -> ProjectExperience:
        await self.ensure_person(person_id)

        project = ProjectExperience(
            **data.model_dump(),
            organization_id=self.organization_id,
            person_id=person_id,
        )

        self.projects.add(project)

        await self.session.commit()
        await self.session.refresh(project)

        return project

    async def update_project(
        self,
        person_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectUpdate,
    ) -> ProjectExperience:
        await self.ensure_person(person_id)

        project = await self.projects.get(
            person_id,
            project_id,
        )

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project experience not found",
            )

        values = data.model_dump(exclude_unset=True)

        new_start_date = values.get(
            "start_date",
            project.start_date,
        )

        new_end_date = values.get(
            "end_date",
            project.end_date,
        )

        new_is_current = values.get(
            "is_current",
            project.is_current,
        )

        self.validate_dates(
            start_date=new_start_date,
            end_date=new_end_date,
            is_current=new_is_current,
            current_label="project",
        )

        for field, value in values.items():
            setattr(project, field, value)

        await self.session.commit()
        await self.session.refresh(project)

        return project

    async def delete_project(
        self,
        person_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        await self.ensure_person(person_id)

        project = await self.projects.get(
            person_id,
            project_id,
        )

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project experience not found",
            )

        await self.session.delete(project)
        await self.session.commit()
