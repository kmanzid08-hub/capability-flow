import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.opportunity_enums import (
    AnalysisStatus,
    MatchStatus,
    OpportunitySourceType,
    OpportunityStatus,
    RequirementImportance,
    RequirementType,
    TeamStatus,
)


class Opportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        Index("ix_opportunities_organization_status", "organization_id", "status"),
        Index("ix_opportunities_organization_deadline", "organization_id", "deadline_at"),
        Index("ix_opportunities_external", "organization_id", "external_source", "external_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(300))
    reference_number: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[OpportunityStatus] = mapped_column(
        Enum(OpportunityStatus, native_enum=False, length=40),
        default=OpportunityStatus.NEW,
        nullable=False,
    )
    external_source: Mapped[str | None] = mapped_column(String(150))
    external_id: Mapped[str | None] = mapped_column(String(300))

    selected_team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("recommended_teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_team_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selected_team_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    internal_notes: Mapped[str | None] = mapped_column(Text)
    outcome_notes: Mapped[str | None] = mapped_column(Text)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )


class OpportunitySource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunity_sources"
    __table_args__ = (
        Index("ix_opportunity_sources_org_opportunity", "organization_id", "opportunity_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[OpportunitySourceType] = mapped_column(
        Enum(OpportunitySourceType, native_enum=False, length=40), nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(2000))
    original_filename: Mapped[str | None] = mapped_column(String(500))
    stored_filename: Mapped[str | None] = mapped_column(String(500))
    storage_path: Mapped[str | None] = mapped_column(String(2000))
    file_size: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(255))
    raw_text: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    external_source: Mapped[str | None] = mapped_column(String(150))
    external_id: Mapped[str | None] = mapped_column(String(300))
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )


class OpportunityAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunity_analyses"
    __table_args__ = (
        Index("ix_opportunity_analyses_org_opportunity", "organization_id", "opportunity_id"),
        Index("ix_opportunity_analyses_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, native_enum=False, length=40),
        default=AnalysisStatus.QUEUED,
        nullable=False,
    )
    model_name: Mapped[str | None] = mapped_column(String(150))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_snapshot: Mapped[str | None] = mapped_column(Text)
    extracted_summary: Mapped[str | None] = mapped_column(Text)
    extracted_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    readiness_score: Mapped[float | None] = mapped_column(Float)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )


class OpportunityRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunity_roles"
    __table_args__ = (
        Index("ix_opportunity_roles_org_analysis", "organization_id", "analysis_id"),
        Index("ix_opportunity_roles_org_title", "organization_id", "title"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OpportunityRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunity_requirements"
    __table_args__ = (
        Index("ix_opportunity_requirements_org_role", "organization_id", "role_id"),
        Index("ix_opportunity_requirements_org_type", "organization_id", "requirement_type"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_type: Mapped[RequirementType] = mapped_column(
        Enum(RequirementType, native_enum=False, length=50), nullable=False
    )
    importance: Mapped[RequirementImportance] = mapped_column(
        Enum(RequirementImportance, native_enum=False, length=30), nullable=False
    )
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(String(500))
    values_json: Mapped[list[str] | None] = mapped_column(JSON)
    minimum_years: Mapped[float | None] = mapped_column(Float)
    minimum_count: Mapped[int | None] = mapped_column(Integer)
    minimum_degree_level: Mapped[str | None] = mapped_column(String(50))
    operator: Mapped[str] = mapped_column(String(30), default="match", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source_excerpt: Mapped[str | None] = mapped_column(Text)


class TeamRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "team_requirements"
    __table_args__ = (Index("ix_team_requirements_org_analysis", "organization_id", "analysis_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_type: Mapped[RequirementType] = mapped_column(
        Enum(RequirementType, native_enum=False, length=50), nullable=False
    )
    importance: Mapped[RequirementImportance] = mapped_column(
        Enum(RequirementImportance, native_enum=False, length=30), nullable=False
    )
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(String(500))
    values_json: Mapped[list[str] | None] = mapped_column(JSON)
    minimum_count: Mapped[int | None] = mapped_column(Integer)
    minimum_years: Mapped[float | None] = mapped_column(Float)
    operator: Mapped[str] = mapped_column(String(30), default="match", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_excerpt: Mapped[str | None] = mapped_column(Text)


class CandidateMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_matches"
    __table_args__ = (
        Index("ix_candidate_matches_org_role_score", "organization_id", "role_id", "score"),
        Index("ix_candidate_matches_org_person", "organization_id", "person_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    mandatory_pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    preferred_pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    mandatory_failed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)
    explanation: Mapped[str | None] = mapped_column(Text)


class RequirementMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "requirement_matches"
    __table_args__ = (
        Index("ix_requirement_matches_org_candidate", "organization_id", "candidate_match_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_match_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("candidate_matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("opportunity_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, native_enum=False, length=30), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_json: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    explanation: Mapped[str | None] = mapped_column(Text)


class RecommendedTeam(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommended_teams"
    __table_args__ = (
        Index("ix_recommended_teams_org_analysis_score", "organization_id", "analysis_id", "score"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[TeamStatus] = mapped_column(
        Enum(TeamStatus, native_enum=False, length=30),
        default=TeamStatus.RECOMMENDED,
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    mandatory_constraints_satisfied: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)


class RecommendedTeamMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommended_team_members"
    __table_args__ = (Index("ix_recommended_team_members_org_team", "organization_id", "team_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recommended_teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_match_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("candidate_matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_score: Mapped[float] = mapped_column(Float, nullable=False)


class CapabilityGap(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "capability_gaps"
    __table_args__ = (Index("ix_capability_gaps_org_analysis", "organization_id", "analysis_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunity_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("opportunity_roles.id", ondelete="CASCADE")
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("opportunity_requirements.id", ondelete="CASCADE")
    )
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    best_candidate_person_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("people.id", ondelete="SET NULL")
    )
    best_candidate_score: Mapped[float | None] = mapped_column(Float)
    recommendation: Mapped[str | None] = mapped_column(Text)
