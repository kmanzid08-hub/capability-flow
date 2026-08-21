import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EmploymentExperience(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "employment_experiences"
    __table_args__ = (
        Index(
            "ix_employment_experiences_org_person",
            "organization_id",
            "person_id",
        ),
        Index(
            "ix_employment_experiences_org_employer",
            "organization_id",
            "employer_name",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "organizations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    employer_name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    job_title: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    employment_type: Mapped[str | None] = mapped_column(
        String(50),
    )

    industry: Mapped[str | None] = mapped_column(
        String(150),
    )

    location: Mapped[str | None] = mapped_column(
        String(250),
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    responsibilities: Mapped[str | None] = mapped_column(
        Text,
    )

    achievements: Mapped[str | None] = mapped_column(
        Text,
    )


class ProjectExperience(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "project_experiences"
    __table_args__ = (
        Index(
            "ix_project_experiences_org_person",
            "organization_id",
            "person_id",
        ),
        Index(
            "ix_project_experiences_org_project",
            "organization_id",
            "project_name",
        ),
        Index(
            "ix_project_experiences_org_sector",
            "organization_id",
            "sector",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "organizations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    project_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    client_name: Mapped[str | None] = mapped_column(
        String(250),
    )

    role: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    sector: Mapped[str | None] = mapped_column(
        String(150),
    )

    location: Mapped[str | None] = mapped_column(
        String(250),
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    responsibilities: Mapped[str | None] = mapped_column(
        Text,
    )

    outcomes: Mapped[str | None] = mapped_column(
        Text,
    )

    skills_summary: Mapped[str | None] = mapped_column(
        Text,
    )
