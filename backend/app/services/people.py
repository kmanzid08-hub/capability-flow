import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProfileStatus
from app.models.person import Person
from app.repositories.people import PersonRepository
from app.schemas.person import PersonCreate, PersonUpdate


class PersonService:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id
        self.user_id = user_id
        self.repository = PersonRepository(
            session,
            organization_id,
        )

    async def create(self, data: PersonCreate) -> Person:
        values = data.model_dump()

        values["display_name"] = data.display_name or " ".join(
            part
            for part in (
                data.first_name,
                data.middle_name,
                data.last_name,
            )
            if part
        )

        person = Person(
            **values,
            organization_id=self.organization_id,
            created_by_user_id=self.user_id,
            updated_by_user_id=self.user_id,
        )

        self.repository.add(person)

        await self.session.commit()
        await self.session.refresh(person)

        return person

    async def get_or_404(
        self,
        person_id: uuid.UUID,
    ) -> Person:
        person = await self.repository.get(person_id)

        if person is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person not found",
            )

        return person

    async def update(
        self,
        person_id: uuid.UUID,
        data: PersonUpdate,
    ) -> Person:
        person = await self.get_or_404(person_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(person, field, value)

        person.updated_by_user_id = self.user_id

        await self.session.commit()
        await self.session.refresh(person)

        return person

    async def archive(
        self,
        person_id: uuid.UUID,
    ) -> None:
        person = await self.get_or_404(person_id)

        person.profile_status = ProfileStatus.ARCHIVED
        person.updated_by_user_id = self.user_id

        await self.session.commit()
