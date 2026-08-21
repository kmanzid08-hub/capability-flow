import uuid
from datetime import date

from sqlalchemy import (
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DegreeLevel, SkillProficiency


class PersonSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "person_skills"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "person_id",
            "name",
            name="uq_person_skill_organization_person_name",
        ),
        Index(
            "ix_person_skills_organization_name",
            "organization_id",
            "name",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("people.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    proficiency: Mapped[SkillProficiency | None] = mapped_column(
        Enum(SkillProficiency, native_enum=False),
        nullable=True,
    )

    years_experience: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    last_used_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )


class PersonEducation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "person_education"
    __table_args__ = (
        Index(
            "ix_person_education_organization_degree",
            "organization_id",
            "degree_level",
        ),
        Index(
            "ix_person_education_organization_field",
            "organization_id",
            "field_of_study",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("people.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    degree_level: Mapped[DegreeLevel] = mapped_column(
        Enum(DegreeLevel, native_enum=False),
        nullable=False,
    )

    degree_name: Mapped[str | None] = mapped_column(
        String(250),
    )

    field_of_study: Mapped[str | None] = mapped_column(
        String(200),
    )

    institution: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
    )

    start_year: Mapped[int | None] = mapped_column(
        Integer,
    )

    graduation_year: Mapped[int | None] = mapped_column(
        Integer,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )


class PersonCertification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "person_certifications"
    __table_args__ = (
        Index(
            "ix_person_certifications_organization_name",
            "organization_id",
            "name",
        ),
        Index(
            "ix_person_certifications_organization_issuer",
            "organization_id",
            "issuer",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("people.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    issuer: Mapped[str | None] = mapped_column(
        String(250),
    )

    credential_id: Mapped[str | None] = mapped_column(
        String(200),
    )

    issue_date: Mapped[date | None] = mapped_column(
        Date,
    )

    expiry_date: Mapped[date | None] = mapped_column(
        Date,
    )

    verification_url: Mapped[str | None] = mapped_column(
        String(1000),
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )
