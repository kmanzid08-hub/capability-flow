"""Add opportunity operations and management workflow metadata."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0006"
down_revision: str | None = "20260818_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("selected_team_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("selected_team_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("selected_team_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("decision_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("outcome_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("outcome_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("internal_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("outcome_notes", sa.Text(), nullable=True),
    )

    op.create_foreign_key(
        "fk_opportunities_selected_team_id_recommended_teams",
        "opportunities",
        "recommended_teams",
        ["selected_team_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_selected_team_by_user_id_users",
        "opportunities",
        "users",
        ["selected_team_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_decision_by_user_id_users",
        "opportunities",
        "users",
        ["decision_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_submitted_by_user_id_users",
        "opportunities",
        "users",
        ["submitted_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_outcome_by_user_id_users",
        "opportunities",
        "users",
        ["outcome_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_opportunities_organization_selected_team",
        "opportunities",
        ["organization_id", "selected_team_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunities_organization_selected_team",
        table_name="opportunities",
    )
    op.drop_constraint(
        "fk_opportunities_outcome_by_user_id_users",
        "opportunities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_opportunities_submitted_by_user_id_users",
        "opportunities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_opportunities_decision_by_user_id_users",
        "opportunities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_opportunities_selected_team_by_user_id_users",
        "opportunities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_opportunities_selected_team_id_recommended_teams",
        "opportunities",
        type_="foreignkey",
    )

    for column in (
        "outcome_notes",
        "internal_notes",
        "outcome_by_user_id",
        "outcome_at",
        "submitted_by_user_id",
        "submitted_at",
        "decision_by_user_id",
        "decision_at",
        "selected_team_by_user_id",
        "selected_team_at",
        "selected_team_id",
    ):
        op.drop_column("opportunities", column)
