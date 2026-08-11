"""Initial organizations, users, memberships, and people schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("status", sa.String(9), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)
    op.create_table(
        "users",
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "organization_memberships",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name=op.f("fk_organization_memberships_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_organization_memberships_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_memberships")),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_organization_user"),
    )
    op.create_index(
        op.f("ix_organization_memberships_organization_id"),
        "organization_memberships",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_organization_memberships_user_id"), "organization_memberships", ["user_id"]
    )
    op.create_table(
        "people",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("middle_name", sa.String(100)),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(250), nullable=False),
        sa.Column("professional_title", sa.String(200)),
        sa.Column("primary_email", sa.String(320)),
        sa.Column("primary_phone", sa.String(50)),
        sa.Column("nationality", sa.String(100)),
        sa.Column("country_of_residence", sa.String(100)),
        sa.Column("summary", sa.Text()),
        sa.Column("availability_status", sa.String(19), nullable=False),
        sa.Column("profile_status", sa.String(8), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name=op.f("fk_people_created_by_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name=op.f("fk_people_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], name=op.f("fk_people_updated_by_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_people")),
    )
    op.create_index(op.f("ix_people_organization_id"), "people", ["organization_id"])
    op.create_index(
        "ix_people_organization_profile", "people", ["organization_id", "profile_status"]
    )


def downgrade() -> None:
    op.drop_table("people")
    op.drop_table("organization_memberships")
    op.drop_table("users")
    op.drop_table("organizations")
