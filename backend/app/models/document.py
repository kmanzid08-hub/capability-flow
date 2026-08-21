import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DocumentType


class PersonDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "person_documents"
    __table_args__ = (
        Index(
            "ix_person_documents_organization_person",
            "organization_id",
            "person_id",
        ),
        Index(
            "ix_person_documents_organization_type",
            "organization_id",
            "document_type",
        ),
        Index(
            "ix_person_documents_certification",
            "certification_id",
        ),
        Index(
            "ix_person_documents_education",
            "education_id",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False, length=32),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    certification_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("person_certifications.id", ondelete="SET NULL"),
        nullable=True,
    )
    education_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("person_education.id", ondelete="SET NULL"),
        nullable=True,
    )
    analysis_status: Mapped[str] = mapped_column(
        String(32),
        default="not_analyzed",
        nullable=False,
    )
    last_analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    analysis_error: Mapped[str | None] = mapped_column(Text)
