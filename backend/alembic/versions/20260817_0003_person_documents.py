"""Add private person document metadata."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260817_0003"
down_revision: str | None = "20260811_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "person_documents",
        sa.Column(
            "organization_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "document_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=250),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "storage_key",
            sa.String(length=1000),
            nullable=False,
        ),
        sa.Column(
            "mime_type",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "file_extension",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "file_size",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_user_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "certification_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "education_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name=op.f("fk_person_documents_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
            ondelete="CASCADE",
            name=op.f("fk_person_documents_person_id_people"),
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_person_documents_uploaded_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["certification_id"],
            ["person_certifications.id"],
            ondelete="SET NULL",
            name=op.f("fk_person_documents_certification_id_person_certifications"),
        ),
        sa.ForeignKeyConstraint(
            ["education_id"],
            ["person_education.id"],
            ondelete="SET NULL",
            name=op.f("fk_person_documents_education_id_person_education"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_person_documents"),
        ),
        sa.UniqueConstraint(
            "storage_key",
            name=op.f("uq_person_documents_storage_key"),
        ),
    )

    op.create_index(
        op.f("ix_person_documents_organization_id"),
        "person_documents",
        ["organization_id"],
    )

    op.create_index(
        op.f("ix_person_documents_person_id"),
        "person_documents",
        ["person_id"],
    )

    op.create_index(
        "ix_person_documents_organization_person",
        "person_documents",
        [
            "organization_id",
            "person_id",
        ],
    )

    op.create_index(
        "ix_person_documents_organization_type",
        "person_documents",
        [
            "organization_id",
            "document_type",
        ],
    )

    op.create_index(
        "ix_person_documents_certification",
        "person_documents",
        ["certification_id"],
    )

    op.create_index(
        "ix_person_documents_education",
        "person_documents",
        ["education_id"],
    )


def downgrade() -> None:
    op.drop_table(
        "person_documents",
    )
