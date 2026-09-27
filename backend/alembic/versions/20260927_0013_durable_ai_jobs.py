"""Add durable AI job queue with leases and retries."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0013"
down_revision: str | None = "20260919_0012"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("active_key", sa.String(length=500), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(length=200), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_jobs_queue",
        "ai_jobs",
        ["status", "available_at", "priority", "created_at"],
    )
    op.create_index(
        "ix_ai_jobs_organization_status",
        "ai_jobs",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_ai_jobs_user_status",
        "ai_jobs",
        ["requested_by_user_id", "status"],
    )
    op.create_index(
        "ix_ai_jobs_entity",
        "ai_jobs",
        ["organization_id", "job_type", "entity_id"],
    )
    op.create_index(
        "uq_ai_jobs_active_key",
        "ai_jobs",
        ["active_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_ai_jobs_active_key", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_entity", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_user_status", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_organization_status", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_queue", table_name="ai_jobs")
    op.drop_table("ai_jobs")
