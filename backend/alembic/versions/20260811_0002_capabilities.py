"""Add skills, education, and certifications."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260811_0002"
down_revision: str | None = "20260731_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "person_skills",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("proficiency", sa.String(12), nullable=True),
        sa.Column("years_experience", sa.Float(), nullable=True),
        sa.Column("last_used_year", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
            name=op.f("fk_person_skills_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
            ondelete="CASCADE",
            name=op.f("fk_person_skills_person_id_people"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_person_skills"),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "person_id",
            "name",
            name="uq_person_skill_organization_person_name",
        ),
    )

    op.create_index(
        op.f("ix_person_skills_organization_id"),
        "person_skills",
        ["organization_id"],
    )

    op.create_index(
        op.f("ix_person_skills_person_id"),
        "person_skills",
        ["person_id"],
    )

    op.create_index(
        "ix_person_skills_organization_name",
        "person_skills",
        ["organization_id", "name"],
    )

    op.create_table(
        "person_education",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("degree_level", sa.String(12), nullable=False),
        sa.Column("degree_name", sa.String(250), nullable=True),
        sa.Column("field_of_study", sa.String(200), nullable=True),
        sa.Column("institution", sa.String(250), nullable=False),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
            name=op.f("fk_person_education_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
            ondelete="CASCADE",
            name=op.f("fk_person_education_person_id_people"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_person_education"),
        ),
    )

    op.create_index(
        op.f("ix_person_education_organization_id"),
        "person_education",
        ["organization_id"],
    )

    op.create_index(
        op.f("ix_person_education_person_id"),
        "person_education",
        ["person_id"],
    )

    op.create_index(
        "ix_person_education_organization_degree",
        "person_education",
        ["organization_id", "degree_level"],
    )

    op.create_index(
        "ix_person_education_organization_field",
        "person_education",
        ["organization_id", "field_of_study"],
    )

    op.create_table(
        "person_certifications",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("issuer", sa.String(250), nullable=True),
        sa.Column("credential_id", sa.String(200), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("verification_url", sa.String(1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
            name=op.f("fk_person_certifications_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
            ondelete="CASCADE",
            name=op.f("fk_person_certifications_person_id_people"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_person_certifications"),
        ),
    )

    op.create_index(
        op.f("ix_person_certifications_organization_id"),
        "person_certifications",
        ["organization_id"],
    )

    op.create_index(
        op.f("ix_person_certifications_person_id"),
        "person_certifications",
        ["person_id"],
    )

    op.create_index(
        "ix_person_certifications_organization_name",
        "person_certifications",
        ["organization_id", "name"],
    )

    op.create_index(
        "ix_person_certifications_organization_issuer",
        "person_certifications",
        ["organization_id", "issuer"],
    )


def downgrade() -> None:
    op.drop_table("person_certifications")
    op.drop_table("person_education")
    op.drop_table("person_skills")
