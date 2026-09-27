import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIJobType(StrEnum):
    DOCUMENT_ANALYSIS = "document_analysis"
    OPPORTUNITY_ANALYSIS = "opportunity_analysis"


class AIJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_AI_JOB_STATUSES = {
    AIJobStatus.QUEUED,
    AIJobStatus.RUNNING,
    AIJobStatus.RETRYING,
}


def utc_now() -> datetime:
    return datetime.now(UTC)


class AIJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_jobs"
    __table_args__ = (
        Index(
            "ix_ai_jobs_queue",
            "status",
            "available_at",
            "priority",
            "created_at",
        ),
        Index(
            "ix_ai_jobs_organization_status",
            "organization_id",
            "status",
        ),
        Index(
            "ix_ai_jobs_user_status",
            "requested_by_user_id",
            "status",
        ),
        Index(
            "ix_ai_jobs_entity",
            "organization_id",
            "job_type",
            "entity_id",
        ),
        Index(
            "uq_ai_jobs_active_key",
            "active_key",
            unique=True,
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[AIJobType] = mapped_column(
        Enum(AIJobType, native_enum=False, length=40),
        nullable=False,
    )
    status: Mapped[AIJobStatus] = mapped_column(
        Enum(AIJobStatus, native_enum=False, length=20),
        default=AIJobStatus.QUEUED,
        nullable=False,
    )
    active_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=True,
    )
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(200))
    last_error_code: Mapped[str | None] = mapped_column(String(100))
    last_error_message: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSON)
