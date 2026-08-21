"""Reconcile automatic opportunity intake source storage.

Revision ID: 20260821_0008
Revises: 20260820_0007
"""

from collections.abc import Sequence

revision: str = "20260821_0008"
down_revision: str | None = "20260820_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The source storage columns are created by 20260820_0007.
    # This no-op revision preserves the already-distributed 0008 identifier.
    pass


def downgrade() -> None:
    pass
