import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.models.opportunity_enums import (
    AnalysisStatus,
    MatchStatus,
    OpportunitySourceType,
    OpportunityStatus,
    RequirementImportance,
    RequirementType,
    TeamStatus,
)
from app.schemas.common import AuditFields


class OpportunityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    client_name: str | None = Field(default=None, max_length=300)
    reference_number: str | None = Field(default=None, max_length=200)
    description: str | None = None
    source_url: HttpUrl | None = None
    deadline_at: datetime | None = None
    external_source: str | None = Field(default=None, max_length=150)
    external_id: str | None = Field(default=None, max_length=300)
    internal_notes: str | None = None


class OpportunityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    client_name: str | None = Field(default=None, max_length=300)
    reference_number: str | None = Field(default=None, max_length=200)
    description: str | None = None
    source_url: HttpUrl | None = None
    deadline_at: datetime | None = None
    status: OpportunityStatus | None = None
    internal_notes: str | None = None
    outcome_notes: str | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "OpportunityUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self


class OpportunityResponse(AuditFields):
    organization_id: uuid.UUID
    title: str
    client_name: str | None
    reference_number: str | None
    description: str | None
    source_url: str | None
    deadline_at: datetime | None
    status: OpportunityStatus
    external_source: str | None
    external_id: str | None

    selected_team_id: uuid.UUID | None
    selected_team_at: datetime | None
    selected_team_by_user_id: uuid.UUID | None

    decision_at: datetime | None
    decision_by_user_id: uuid.UUID | None
    submitted_at: datetime | None
    submitted_by_user_id: uuid.UUID | None
    outcome_at: datetime | None
    outcome_by_user_id: uuid.UUID | None

    internal_notes: str | None
    outcome_notes: str | None

    created_by_user_id: uuid.UUID
    updated_by_user_id: uuid.UUID


class SourceTextCreate(BaseModel):
    text: str = Field(min_length=20)
    source_type: OpportunitySourceType = OpportunitySourceType.PASTED_TEXT
    source_url: HttpUrl | None = None


class SourceUrlCreate(BaseModel):
    url: HttpUrl


class OpportunitySourceResponse(AuditFields):
    opportunity_id: uuid.UUID
    source_type: OpportunitySourceType
    source_url: str | None
    original_filename: str | None
    stored_filename: str | None
    file_size: int | None
    mime_type: str | None
    content_hash: str | None
    metadata_json: dict[str, object] | None
    created_by_user_id: uuid.UUID


class UrlIntakeCreate(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=500)
    client_name: str | None = Field(default=None, max_length=300)


class TextIntakeCreate(BaseModel):
    text: str = Field(min_length=20)
    title: str | None = Field(default=None, max_length=500)
    client_name: str | None = Field(default=None, max_length=300)
    source_url: HttpUrl | None = None


class OpportunityIntakeResponse(BaseModel):
    opportunity: OpportunityResponse
    source: OpportunitySourceResponse


class RequirementDraft(BaseModel):
    requirement_type: RequirementType
    importance: RequirementImportance = RequirementImportance.MANDATORY
    label: str = Field(min_length=1, max_length=500)
    normalized_value: str | None = Field(default=None, max_length=500)
    values: list[str] | None = None
    minimum_years: float | None = Field(default=None, ge=0, le=100)
    minimum_count: int | None = Field(default=None, ge=0, le=1000)
    minimum_degree_level: str | None = Field(default=None, max_length=50)
    operator: str = Field(default="match", max_length=30)
    weight: float = Field(default=1.0, gt=0, le=100)
    evidence_required: bool = False
    notes: str | None = None
    source_excerpt: str | None = None


class RoleDraft(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    quantity: int = Field(default=1, ge=1, le=100)
    is_mandatory: bool = True
    requirements: list[RequirementDraft] = Field(default_factory=list)


class TeamRequirementDraft(BaseModel):
    requirement_type: RequirementType
    importance: RequirementImportance = RequirementImportance.MANDATORY
    label: str = Field(min_length=1, max_length=500)
    normalized_value: str | None = Field(default=None, max_length=500)
    values: list[str] | None = None
    minimum_count: int | None = Field(default=None, ge=0, le=1000)
    minimum_years: float | None = Field(default=None, ge=0, le=100)
    operator: str = Field(default="match", max_length=30)
    weight: float = Field(default=1.0, gt=0, le=100)
    source_excerpt: str | None = None


class ExtractedOpportunity(BaseModel):
    title: str | None = None
    client_name: str | None = None
    reference_number: str | None = None
    deadline_at: datetime | None = None
    summary: str
    roles: list[RoleDraft]
    team_requirements: list[TeamRequirementDraft] = Field(default_factory=list)


class RequirementResponse(AuditFields):
    role_id: uuid.UUID
    requirement_type: RequirementType
    importance: RequirementImportance
    label: str
    normalized_value: str | None
    values_json: list[str] | None
    minimum_years: float | None
    minimum_count: int | None
    minimum_degree_level: str | None
    operator: str
    weight: float
    evidence_required: bool
    notes: str | None
    source_excerpt: str | None


class RoleResponse(AuditFields):
    opportunity_id: uuid.UUID
    analysis_id: uuid.UUID
    title: str
    description: str | None
    quantity: int
    is_mandatory: bool
    sort_order: int
    requirements: list[RequirementResponse] = Field(default_factory=list)


class RequirementMatchResponse(AuditFields):
    requirement_id: uuid.UUID
    status: MatchStatus
    score: float
    evidence_json: list[dict[str, object]] | None
    explanation: str | None


class CandidateMatchResponse(AuditFields):
    role_id: uuid.UUID
    person_id: uuid.UUID
    score: float
    mandatory_pass_rate: float
    preferred_pass_rate: float
    mandatory_failed: bool
    rank: int | None
    explanation: str | None
    person_name: str | None = None
    professional_title: str | None = None
    requirement_matches: list[RequirementMatchResponse] = Field(default_factory=list)


class RecommendedTeamMemberResponse(AuditFields):
    role_id: uuid.UUID
    person_id: uuid.UUID
    candidate_match_id: uuid.UUID
    assignment_score: float
    person_name: str | None = None
    role_title: str | None = None


class RecommendedTeamResponse(AuditFields):
    analysis_id: uuid.UUID
    name: str
    status: TeamStatus
    score: float
    mandatory_constraints_satisfied: bool
    explanation: str | None
    members: list[RecommendedTeamMemberResponse] = Field(default_factory=list)


class CapabilityGapResponse(AuditFields):
    analysis_id: uuid.UUID
    role_id: uuid.UUID | None
    requirement_id: uuid.UUID | None
    severity: str
    label: str
    best_candidate_person_id: uuid.UUID | None
    best_candidate_score: float | None
    recommendation: str | None


class AnalysisResponse(AuditFields):
    opportunity_id: uuid.UUID
    version: int
    status: AnalysisStatus
    model_name: str | None
    started_at: datetime | None
    completed_at: datetime | None
    extracted_summary: str | None
    error_message: str | None
    readiness_score: float | None
