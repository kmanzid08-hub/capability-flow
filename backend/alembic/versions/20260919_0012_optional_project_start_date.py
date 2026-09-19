"""Allow project evidence when the source does not state a start date."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260919_0012"
down_revision: str | None = "20260909_0011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "project_experiences",
        "start_date",
        existing_type=sa.String(length=10),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    # Do not fabricate dates. This downgrade is intentionally blocked by the
    # database if undated project rows still exist.
    op.alter_column(
        "project_experiences",
        "start_date",
        existing_type=sa.String(length=10),
        existing_nullable=True,
        nullable=False,
    )
