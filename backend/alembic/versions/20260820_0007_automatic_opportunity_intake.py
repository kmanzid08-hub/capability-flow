"""Persist original opportunity source snapshots.

Revision ID: 20260820_0007
Revises: 20260820_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0007"
down_revision: str | None = "20260820_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunity_sources",
        sa.Column("stored_filename", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "opportunity_sources",
        sa.Column("storage_path", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "opportunity_sources",
        sa.Column("file_size", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("opportunity_sources", "file_size")
    op.drop_column("opportunity_sources", "storage_path")
    op.drop_column("opportunity_sources", "stored_filename")
