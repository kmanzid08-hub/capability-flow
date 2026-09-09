from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260909_0011"
down_revision: str | None = "20260909_0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "person_education",
        sa.Column("start_date", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "person_education",
        sa.Column("graduation_date", sa.String(length=10), nullable=True),
    )
    op.execute(
        "UPDATE person_education SET start_date = start_year::text WHERE start_year IS NOT NULL"
    )
    op.execute(
        "UPDATE person_education SET graduation_date = graduation_year::text "
        "WHERE graduation_year IS NOT NULL"
    )
    op.drop_column("person_education", "start_year")
    op.drop_column("person_education", "graduation_year")

    for column in ("issue_date", "expiry_date"):
        op.alter_column(
            "person_certifications",
            column,
            existing_type=sa.Date(),
            type_=sa.String(length=10),
            existing_nullable=True,
            postgresql_using=f"{column}::text",
        )


def downgrade() -> None:
    op.add_column(
        "person_education",
        sa.Column("start_year", sa.Integer(), nullable=True),
    )
    op.add_column(
        "person_education",
        sa.Column("graduation_year", sa.Integer(), nullable=True),
    )
    op.execute(
        "UPDATE person_education SET start_year = substring(start_date from 1 for 4)::integer "
        "WHERE start_date IS NOT NULL"
    )
    op.execute(
        "UPDATE person_education SET graduation_year = "
        "substring(graduation_date from 1 for 4)::integer "
        "WHERE graduation_date IS NOT NULL"
    )
    op.drop_column("person_education", "start_date")
    op.drop_column("person_education", "graduation_date")

    op.alter_column(
        "person_certifications",
        "issue_date",
        existing_type=sa.String(length=10),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using=(
            "CASE "
            "WHEN issue_date IS NULL THEN NULL "
            "WHEN char_length(issue_date) = 4 THEN (issue_date || '-01-01')::date "
            "WHEN char_length(issue_date) = 7 THEN (issue_date || '-01')::date "
            "ELSE issue_date::date END"
        ),
    )
    op.alter_column(
        "person_certifications",
        "expiry_date",
        existing_type=sa.String(length=10),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using=(
            "CASE "
            "WHEN expiry_date IS NULL THEN NULL "
            "WHEN char_length(expiry_date) = 4 THEN (expiry_date || '-12-31')::date "
            "WHEN char_length(expiry_date) = 7 THEN "
            "(date_trunc('month', (expiry_date || '-01')::date) + "
            "interval '1 month - 1 day')::date "
            "ELSE expiry_date::date END"
        ),
    )
