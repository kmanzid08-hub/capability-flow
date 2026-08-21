import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import PersonDocument


class DocumentRepository:
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
    ) -> list[PersonDocument]:
        result = await self.session.scalars(
            select(PersonDocument)
            .where(
                PersonDocument.organization_id == self.organization_id,
                PersonDocument.person_id == person_id,
            )
            .order_by(
                PersonDocument.created_at.desc(),
            )
        )

        return list(result)

    async def get(
        self,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> PersonDocument | None:
        result = await self.session.scalars(
            select(PersonDocument).where(
                PersonDocument.id == document_id,
                PersonDocument.person_id == person_id,
                PersonDocument.organization_id == self.organization_id,
            )
        )

        return result.first()

    def add(
        self,
        document: PersonDocument,
    ) -> None:
        if document.organization_id != self.organization_id:
            raise ValueError("Document organization does not match repository context")

        self.session.add(document)
