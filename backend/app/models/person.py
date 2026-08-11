import uuid

from sqlalchemy import Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AvailabilityStatus, ProfileStatus


class Person(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "people"
    __table_args__ = (Index("ix_people_organization_profile", "organization_id", "profile_status"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(250), nullable=False)
    professional_title: Mapped[str | None] = mapped_column(String(200))
    primary_email: Mapped[str | None] = mapped_column(String(320))
    primary_phone: Mapped[str | None] = mapped_column(String(50))
    nationality: Mapped[str | None] = mapped_column(String(100))
    country_of_residence: Mapped[str | None] = mapped_column(String(100))
    summary: Mapped[str | None] = mapped_column(Text)
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        Enum(AvailabilityStatus, native_enum=False),
        default=AvailabilityStatus.UNKNOWN,
        nullable=False,
    )
    profile_status: Mapped[ProfileStatus] = mapped_column(
        Enum(ProfileStatus, native_enum=False), default=ProfileStatus.DRAFT, nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
