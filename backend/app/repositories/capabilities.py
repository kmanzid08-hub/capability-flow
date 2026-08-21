import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capability import (
    PersonCertification,
    PersonEducation,
    PersonSkill,
)


class SkillRepository:
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
    ) -> list[PersonSkill]:
        result = await self.session.scalars(
            select(PersonSkill)
            .where(
                PersonSkill.organization_id == self.organization_id,
                PersonSkill.person_id == person_id,
            )
            .order_by(PersonSkill.name)
        )
        return list(result)

    async def get(
        self,
        person_id: uuid.UUID,
        skill_id: uuid.UUID,
    ) -> PersonSkill | None:
        result = await self.session.scalars(
            select(PersonSkill).where(
                PersonSkill.id == skill_id,
                PersonSkill.person_id == person_id,
                PersonSkill.organization_id == self.organization_id,
            )
        )
        return result.first()

    async def get_by_name(
        self,
        person_id: uuid.UUID,
        name: str,
    ) -> PersonSkill | None:
        result = await self.session.scalars(
            select(PersonSkill).where(
                PersonSkill.organization_id == self.organization_id,
                PersonSkill.person_id == person_id,
                PersonSkill.name == name,
            )
        )
        return result.first()

    def add(self, skill: PersonSkill) -> None:
        if skill.organization_id != self.organization_id:
            raise ValueError("Skill organization does not match repository context")
        self.session.add(skill)


class EducationRepository:
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
    ) -> list[PersonEducation]:
        result = await self.session.scalars(
            select(PersonEducation)
            .where(
                PersonEducation.organization_id == self.organization_id,
                PersonEducation.person_id == person_id,
            )
            .order_by(
                PersonEducation.graduation_year.desc(),
                PersonEducation.created_at.desc(),
            )
        )
        return list(result)

    async def get(
        self,
        person_id: uuid.UUID,
        education_id: uuid.UUID,
    ) -> PersonEducation | None:
        result = await self.session.scalars(
            select(PersonEducation).where(
                PersonEducation.id == education_id,
                PersonEducation.person_id == person_id,
                PersonEducation.organization_id == self.organization_id,
            )
        )
        return result.first()

    def add(self, education: PersonEducation) -> None:
        if education.organization_id != self.organization_id:
            raise ValueError("Education organization does not match repository context")
        self.session.add(education)


class CertificationRepository:
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
    ) -> list[PersonCertification]:
        result = await self.session.scalars(
            select(PersonCertification)
            .where(
                PersonCertification.organization_id == self.organization_id,
                PersonCertification.person_id == person_id,
            )
            .order_by(
                PersonCertification.issue_date.desc(),
                PersonCertification.name,
            )
        )
        return list(result)

    async def get(
        self,
        person_id: uuid.UUID,
        certification_id: uuid.UUID,
    ) -> PersonCertification | None:
        result = await self.session.scalars(
            select(PersonCertification).where(
                PersonCertification.id == certification_id,
                PersonCertification.person_id == person_id,
                PersonCertification.organization_id == self.organization_id,
            )
        )
        return result.first()

    def add(self, certification: PersonCertification) -> None:
        if certification.organization_id != self.organization_id:
            raise ValueError("Certification organization does not match repository context")
        self.session.add(certification)
