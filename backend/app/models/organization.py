from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OrganizationStatus

if TYPE_CHECKING:
    from app.models.membership import OrganizationMembership


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(OrganizationStatus, native_enum=False),
        default=OrganizationStatus.ACTIVE,
        nullable=False,
    )
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="organization"
    )
