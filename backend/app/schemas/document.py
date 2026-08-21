import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import DocumentType
from app.schemas.common import AuditFields


class DocumentResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID

    document_type: DocumentType

    title: str
    description: str | None

    original_filename: str
    mime_type: str
    file_extension: str
    file_size: int

    uploaded_by_user_id: uuid.UUID

    certification_id: uuid.UUID | None
    education_id: uuid.UUID | None

    analysis_status: str
    last_analyzed_at: datetime | None
    analysis_error: str | None


class DocumentMetadataUpdate(BaseModel):
    document_type: DocumentType | None = None

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )

    description: str | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "DocumentMetadataUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self
