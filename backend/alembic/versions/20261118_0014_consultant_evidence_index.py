"""Add organization-scoped pgvector index for consultant evidence (opt-in)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261118_0014"
down_revision: str | None = "20260927_0013"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # The extension is available on PostgreSQL providers such as Neon; failing
    # explicitly is preferable to silently creating an unusable semantic index.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "consultant_evidence_index",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "person_id", "evidence_type", "evidence_id"),
    )
    op.execute("ALTER TABLE consultant_evidence_index ADD COLUMN embedding vector(1536)")
    op.create_index(
        "ix_consultant_evidence_person",
        "consultant_evidence_index",
        ["organization_id", "person_id"],
    )
    op.execute(
        "CREATE INDEX ix_consultant_evidence_lexical "
        "ON consultant_evidence_index USING gin "
        "(to_tsvector('simple', content))"
    )
    # Exact distance search initially: no approximate-index recall loss.
    # ANN/HNSW can be added later after benchmarking the candidate pool.


def downgrade() -> None:
    op.drop_index("ix_consultant_evidence_lexical", table_name="consultant_evidence_index")
    op.drop_index("ix_consultant_evidence_person", table_name="consultant_evidence_index")
    op.drop_table("consultant_evidence_index")
    # Do not drop vector: other applications may use the extension.
