import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from fastapi import (
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.document import PersonDocument
from app.models.enums import DocumentType
from app.repositories.capabilities import (
    CertificationRepository,
    EducationRepository,
)
from app.repositories.documents import (
    DocumentRepository,
)
from app.repositories.people import PersonRepository
from app.schemas.document import (
    DocumentMetadataUpdate,
)
from app.services.document_analysis_jobs import document_analysis_job_running
from app.services.document_storage import (
    DocumentTooLarge,
    InvalidDocumentFile,
    create_document_storage,
)
from app.services.document_text import UnsupportedAnalysisDocument, extract_text


@dataclass(frozen=True)
class DocumentDownload:
    document: PersonDocument
    content: bytes


logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id
        self.user_id = user_id

        settings = get_settings()
        self.settings = settings

        self.storage = create_document_storage(settings)

        self.people = PersonRepository(
            session,
            organization_id,
        )

        self.documents = DocumentRepository(
            session,
            organization_id,
        )

        self.certifications = CertificationRepository(
            session,
            organization_id,
        )

        self.education = EducationRepository(
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
                status_code=(status.HTTP_404_NOT_FOUND),
                detail="Person not found",
            )

    _PROCESSING_TIMEOUT = timedelta(minutes=60)

    @classmethod
    def _processing_reference(cls, document: PersonDocument) -> datetime | None:
        value = getattr(document, "updated_at", None)
        if value is None:
            value = getattr(document, "last_analyzed_at", None)
        if value is None:
            value = getattr(document, "created_at", None)
        if value is None:
            return None
        typed_value = cast(datetime, value)
        if typed_value.tzinfo is None:
            return typed_value.replace(tzinfo=UTC)
        return typed_value

    @classmethod
    def _is_stale_processing(cls, document: PersonDocument) -> bool:
        if document.analysis_status != "processing":
            return False
        reference = cls._processing_reference(document)
        if reference is None:
            return True
        return datetime.now(UTC) - reference > cls._PROCESSING_TIMEOUT

    async def _recover_stale_processing(
        self,
        documents: list[PersonDocument],
    ) -> None:
        changed_documents: list[PersonDocument] = []
        for document in documents:
            if document_analysis_job_running(
                self.organization_id,
                document.person_id,
                document.id,
            ):
                continue
            if not self._is_stale_processing(document):
                continue
            document.analysis_status = "failed"
            document.analysis_error = (
                "Document analysis was stopped because it remained in Processing "
                "for more than 60 minutes. The document is safe. Start Analyze again."
            )
            document.last_analyzed_at = datetime.now(UTC)
            changed_documents.append(document)
            logger.warning(
                "Recovered stale document analysis: person_id=%s document_id=%s",
                document.person_id,
                document.id,
            )
        if changed_documents:
            await self.session.commit()
            # TimestampMixin.updated_at is populated by SQLAlchemy/DB on UPDATE and can be
            # expired after commit. Refresh before FastAPI serializes these ORM objects,
            # otherwise async lazy loading can raise MissingGreenlet.
            for document in changed_documents:
                await self.session.refresh(document)

    async def list_documents(
        self,
        person_id: uuid.UUID,
    ) -> list[PersonDocument]:
        await self.ensure_person(person_id)

        documents = await self.documents.list(person_id)
        await self._recover_stale_processing(documents)
        return documents

    async def upload_document(
        self,
        person_id: uuid.UUID,
        upload: UploadFile,
        document_type: DocumentType,
        title: str | None,
        description: str | None,
        certification_id: uuid.UUID | None,
        education_id: uuid.UUID | None,
    ) -> PersonDocument:
        await self.ensure_person(person_id)

        if certification_id is not None and education_id is not None:
            raise HTTPException(
                status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
                detail=("A document cannot be linked to both a certification and education record"),
            )

        if certification_id is not None:
            certification = await self.certifications.get(
                person_id,
                certification_id,
            )

            if certification is None:
                raise HTTPException(
                    status_code=(status.HTTP_404_NOT_FOUND),
                    detail=("Certification not found"),
                )

        if education_id is not None:
            education = await self.education.get(
                person_id,
                education_id,
            )

            if education is None:
                raise HTTPException(
                    status_code=(status.HTTP_404_NOT_FOUND),
                    detail=("Education record not found"),
                )

        try:
            stored = await self.storage.save(
                upload,
                self.organization_id,
                person_id,
            )
        except DocumentTooLarge as exc:
            raise HTTPException(
                status_code=(status.HTTP_413_CONTENT_TOO_LARGE),
                detail=str(exc),
            ) from exc
        except InvalidDocumentFile as exc:
            raise HTTPException(
                status_code=(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
                detail=str(exc),
            ) from exc

        normalized_title = (
            title.strip()
            if title is not None and title.strip()
            else Path(stored.original_filename).stem
        )

        if len(normalized_title) > 250:
            await self.storage.delete(stored.storage_key)

            raise HTTPException(
                status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
                detail=("Document title cannot exceed 250 characters"),
            )

        document = PersonDocument(
            organization_id=(self.organization_id),
            person_id=person_id,
            document_type=document_type,
            title=normalized_title,
            description=(
                description.strip() if description is not None and description.strip() else None
            ),
            original_filename=(stored.original_filename),
            storage_key=stored.storage_key,
            mime_type=stored.mime_type,
            file_extension=(stored.file_extension),
            file_size=stored.file_size,
            uploaded_by_user_id=self.user_id,
            certification_id=certification_id,
            education_id=education_id,
        )

        self.documents.add(document)

        try:
            await self.session.commit()
            await self.session.refresh(document)
        except Exception:
            await self.session.rollback()
            await self.storage.delete(stored.storage_key)
            raise

        return document

    async def update_document(
        self,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
        data: DocumentMetadataUpdate,
    ) -> PersonDocument:
        await self.ensure_person(person_id)

        document = await self.documents.get(
            person_id,
            document_id,
        )

        if document is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail="Document not found",
            )

        values = data.model_dump(exclude_unset=True)

        if "title" in values and values["title"] is not None:
            values["title"] = values["title"].strip()

        if "description" in values and values["description"] is not None:
            values["description"] = values["description"].strip() or None

        for field, value in values.items():
            setattr(
                document,
                field,
                value,
            )

        await self.session.commit()
        await self.session.refresh(document)

        return document

    async def get_download(
        self,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentDownload:
        await self.ensure_person(person_id)

        document = await self.documents.get(
            person_id,
            document_id,
        )

        if document is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail="Document not found",
            )

        try:
            content = await self.storage.read(document.storage_key)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail=("Document file not found"),
            ) from exc

        return DocumentDownload(
            document=document,
            content=content,
        )

    async def get_text_preview(
        self,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> tuple[PersonDocument, str]:
        download = await self.get_download(person_id, document_id)
        try:
            text = extract_text(
                download.content,
                download.document.file_extension,
                min(self.settings.ai_max_document_chars, 250_000),
            )
        except UnsupportedAnalysisDocument as exc:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    "A text preview is not available for this file type. "
                    "Use Download to open the original file."
                ),
            ) from exc
        return download.document, text

    async def delete_document(
        self,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        await self.ensure_person(person_id)

        document = await self.documents.get(
            person_id,
            document_id,
        )

        if document is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail="Document not found",
            )

        storage_key = document.storage_key

        await self.session.delete(document)
        await self.session.commit()

        await self.storage.delete(storage_key)
