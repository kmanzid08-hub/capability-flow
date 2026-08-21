import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capability import (
    PersonCertification,
    PersonEducation,
    PersonSkill,
)
from app.repositories.capabilities import (
    CertificationRepository,
    EducationRepository,
    SkillRepository,
)
from app.repositories.people import PersonRepository
from app.schemas.capability import (
    CertificationCreate,
    CertificationUpdate,
    EducationCreate,
    EducationUpdate,
    SkillCreate,
    SkillUpdate,
)


class CapabilityService:
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

        self.skills = SkillRepository(
            session,
            organization_id,
        )

        self.education = EducationRepository(
            session,
            organization_id,
        )

        self.certifications = CertificationRepository(
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

    async def list_skills(
        self,
        person_id: uuid.UUID,
    ) -> list[PersonSkill]:
        await self.ensure_person(person_id)
        return await self.skills.list(person_id)

    async def create_skill(
        self,
        person_id: uuid.UUID,
        data: SkillCreate,
    ) -> PersonSkill:
        await self.ensure_person(person_id)

        normalized_name = data.name.strip()

        existing = await self.skills.get_by_name(
            person_id,
            normalized_name,
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This skill already exists for the person",
            )

        values = data.model_dump()
        values["name"] = normalized_name

        skill = PersonSkill(
            **values,
            organization_id=self.organization_id,
            person_id=person_id,
        )

        self.skills.add(skill)

        await self.session.commit()
        await self.session.refresh(skill)

        return skill

    async def update_skill(
        self,
        person_id: uuid.UUID,
        skill_id: uuid.UUID,
        data: SkillUpdate,
    ) -> PersonSkill:
        await self.ensure_person(person_id)

        skill = await self.skills.get(
            person_id,
            skill_id,
        )

        if skill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found",
            )

        values = data.model_dump(exclude_unset=True)

        if "name" in values and values["name"] is not None:
            normalized_name = values["name"].strip()
            values["name"] = normalized_name

            duplicate = await self.skills.get_by_name(
                person_id,
                normalized_name,
            )

            if duplicate is not None and duplicate.id != skill.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This skill already exists for the person",
                )

        for field, value in values.items():
            setattr(skill, field, value)

        await self.session.commit()
        await self.session.refresh(skill)

        return skill

    async def delete_skill(
        self,
        person_id: uuid.UUID,
        skill_id: uuid.UUID,
    ) -> None:
        await self.ensure_person(person_id)

        skill = await self.skills.get(
            person_id,
            skill_id,
        )

        if skill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found",
            )

        await self.session.delete(skill)
        await self.session.commit()

    async def list_education(
        self,
        person_id: uuid.UUID,
    ) -> list[PersonEducation]:
        await self.ensure_person(person_id)
        return await self.education.list(person_id)

    async def create_education(
        self,
        person_id: uuid.UUID,
        data: EducationCreate,
    ) -> PersonEducation:
        await self.ensure_person(person_id)

        education = PersonEducation(
            **data.model_dump(),
            organization_id=self.organization_id,
            person_id=person_id,
        )

        self.education.add(education)

        await self.session.commit()
        await self.session.refresh(education)

        return education

    async def update_education(
        self,
        person_id: uuid.UUID,
        education_id: uuid.UUID,
        data: EducationUpdate,
    ) -> PersonEducation:
        await self.ensure_person(person_id)

        education = await self.education.get(
            person_id,
            education_id,
        )

        if education is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Education record not found",
            )

        values = data.model_dump(exclude_unset=True)

        new_start_year = values.get(
            "start_year",
            education.start_year,
        )

        new_graduation_year = values.get(
            "graduation_year",
            education.graduation_year,
        )

        if (
            new_start_year is not None
            and new_graduation_year is not None
            and new_graduation_year < new_start_year
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=("Graduation year cannot be earlier than start year"),
            )

        for field, value in values.items():
            setattr(education, field, value)

        await self.session.commit()
        await self.session.refresh(education)

        return education

    async def delete_education(
        self,
        person_id: uuid.UUID,
        education_id: uuid.UUID,
    ) -> None:
        await self.ensure_person(person_id)

        education = await self.education.get(
            person_id,
            education_id,
        )

        if education is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Education record not found",
            )

        await self.session.delete(education)
        await self.session.commit()

    async def list_certifications(
        self,
        person_id: uuid.UUID,
    ) -> list[PersonCertification]:
        await self.ensure_person(person_id)
        return await self.certifications.list(person_id)

    async def create_certification(
        self,
        person_id: uuid.UUID,
        data: CertificationCreate,
    ) -> PersonCertification:
        await self.ensure_person(person_id)

        values = data.model_dump()

        if values["verification_url"] is not None:
            values["verification_url"] = str(values["verification_url"])

        certification = PersonCertification(
            **values,
            organization_id=self.organization_id,
            person_id=person_id,
        )

        self.certifications.add(certification)

        await self.session.commit()
        await self.session.refresh(certification)

        return certification

    async def update_certification(
        self,
        person_id: uuid.UUID,
        certification_id: uuid.UUID,
        data: CertificationUpdate,
    ) -> PersonCertification:
        await self.ensure_person(person_id)

        certification = await self.certifications.get(
            person_id,
            certification_id,
        )

        if certification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certification not found",
            )

        values = data.model_dump(exclude_unset=True)

        if "verification_url" in values and values["verification_url"] is not None:
            values["verification_url"] = str(values["verification_url"])

        new_issue_date = values.get(
            "issue_date",
            certification.issue_date,
        )

        new_expiry_date = values.get(
            "expiry_date",
            certification.expiry_date,
        )

        if (
            new_issue_date is not None
            and new_expiry_date is not None
            and new_expiry_date < new_issue_date
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Expiry date cannot be earlier than issue date",
            )

        for field, value in values.items():
            setattr(certification, field, value)

        await self.session.commit()
        await self.session.refresh(certification)

        return certification

    async def delete_certification(
        self,
        person_id: uuid.UUID,
        certification_id: uuid.UUID,
    ) -> None:
        await self.ensure_person(person_id)

        certification = await self.certifications.get(
            person_id,
            certification_id,
        )

        if certification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certification not found",
            )

        await self.session.delete(certification)
        await self.session.commit()
