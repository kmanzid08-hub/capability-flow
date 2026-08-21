import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import AuditFields

SuggestionCategory = Literal[
    "profile", "skill", "education", "certification", "employment", "project"
]
SuggestionStatus = Literal["pending", "accepted", "rejected"]


class ProfileSuggestionResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID
    source_document_id: uuid.UUID
    category: SuggestionCategory
    title: str
    payload: dict[str, Any]
    confidence: float | None
    status: SuggestionStatus
    review_note: str | None
    applied_entity_id: uuid.UUID | None
    created_by_user_id: uuid.UUID
    reviewed_by_user_id: uuid.UUID | None
    reviewed_at: datetime | None


class SuggestionEdit(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    payload: dict[str, Any] | None = None
    review_note: str | None = None


class AnalyzeDocumentResponse(BaseModel):
    document_id: uuid.UUID
    suggestions_created: int
    analysis_status: str


class ProfileCompletenessResponse(BaseModel):
    profile_percent: int
    evidence_percent: int
    sections: dict[str, bool]
    evidence_backed_records: int
    total_structured_records: int
