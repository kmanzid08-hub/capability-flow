"""Add AI profile suggestions and document analysis metadata."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260821_0009"
down_revision: str | None = "20260821_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "person_documents",
        sa.Column(
            "analysis_status", sa.String(length=32), nullable=False, server_default="not_analyzed"
        ),
    )
    op.add_column(
        "person_documents", sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("person_documents", sa.Column("analysis_error", sa.Text(), nullable=True))

    op.create_table(
        "profile_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("applied_entity_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["person_documents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_profile_suggestions_org_person_status",
        "profile_suggestions",
        ["organization_id", "person_id", "status"],
    )
    op.create_index(
        "ix_profile_suggestions_document", "profile_suggestions", ["source_document_id"]
    )

    op.create_table(
        "profile_evidence_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["person_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "document_id",
            "entity_type",
            "entity_id",
            name="uq_profile_evidence_link",
        ),
    )
    op.create_index(
        "ix_profile_evidence_links_person",
        "profile_evidence_links",
        ["organization_id", "person_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_profile_evidence_links_person", table_name="profile_evidence_links")
    op.drop_table("profile_evidence_links")
    op.drop_index("ix_profile_suggestions_document", table_name="profile_suggestions")
    op.drop_index("ix_profile_suggestions_org_person_status", table_name="profile_suggestions")
    op.drop_table("profile_suggestions")
    op.drop_column("person_documents", "analysis_error")
    op.drop_column("person_documents", "last_analyzed_at")
    op.drop_column("person_documents", "analysis_status")
