"""Allow partial dates for employment and project experience."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260909_0010"
down_revision: str | None = "20260821_0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    for table in ("employment_experiences", "project_experiences"):
        op.alter_column(
            table,
            "start_date",
            existing_type=sa.Date(),
            type_=sa.String(length=10),
            existing_nullable=False,
            postgresql_using="start_date::text",
        )
        op.alter_column(
            table,
            "end_date",
            existing_type=sa.Date(),
            type_=sa.String(length=10),
            existing_nullable=True,
            postgresql_using="end_date::text",
        )


def downgrade() -> None:
    for table in ("employment_experiences", "project_experiences"):
        op.alter_column(
            table,
            "start_date",
            existing_type=sa.String(length=10),
            type_=sa.Date(),
            existing_nullable=False,
            postgresql_using=(
                "CASE "
                "WHEN char_length(start_date) = 4 THEN (start_date || '-01-01')::date "
                "WHEN char_length(start_date) = 7 THEN (start_date || '-01')::date "
                "ELSE start_date::date END"
            ),
        )
        op.alter_column(
            table,
            "end_date",
            existing_type=sa.String(length=10),
            type_=sa.Date(),
            existing_nullable=True,
            postgresql_using=(
                "CASE "
                "WHEN end_date IS NULL THEN NULL "
                "WHEN char_length(end_date) = 4 THEN (end_date || '-12-31')::date "
                "WHEN char_length(end_date) = 7 THEN "
                "(date_trunc('month', (end_date || '-01')::date) + "
                "interval '1 month - 1 day')::date "
                "ELSE end_date::date END"
            ),
        )
