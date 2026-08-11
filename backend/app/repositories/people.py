import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProfileStatus
from app.models.person import Person


class PersonRepository:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id

    async def list(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Person], int]:
        tenant_filter = (
            Person.organization_id == self.organization_id,
            Person.profile_status != ProfileStatus.ARCHIVED,
        )

        rows = await self.session.scalars(
            select(Person)
            .where(*tenant_filter)
            .order_by(Person.display_name)
            .limit(limit)
            .offset(offset)
        )

        total = await self.session.scalar(select(func.count(Person.id)).where(*tenant_filter))

        return list(rows), total or 0

    async def get(
        self,
        person_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> Person | None:
        query = select(Person).where(
            Person.id == person_id,
            Person.organization_id == self.organization_id,
        )

        if not include_archived:
            query = query.where(Person.profile_status != ProfileStatus.ARCHIVED)

        result = await self.session.scalars(query)
        return result.first()

    def add(self, person: Person) -> None:
        if person.organization_id != self.organization_id:
            raise ValueError("Person organization does not match repository context")

        self.session.add(person)
