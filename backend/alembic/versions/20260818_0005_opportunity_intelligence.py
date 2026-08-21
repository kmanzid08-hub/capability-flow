"""Add production opportunity intelligence domain."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260818_0005"
down_revision: str | None = "20260817_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def enum_string(length: int) -> sa.String:
    return sa.String(length=length)


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("client_name", sa.String(300)),
        sa.Column("reference_number", sa.String(200)),
        sa.Column("description", sa.Text()),
        sa.Column("source_url", sa.String(2000)),
        sa.Column("deadline_at", sa.DateTime(timezone=True)),
        sa.Column("status", enum_string(40), nullable=False),
        sa.Column("external_source", sa.String(150)),
        sa.Column("external_id", sa.String(300)),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_organization_id", "opportunities", ["organization_id"])
    op.create_index(
        "ix_opportunities_organization_status", "opportunities", ["organization_id", "status"]
    )
    op.create_index(
        "ix_opportunities_organization_deadline",
        "opportunities",
        ["organization_id", "deadline_at"],
    )
    op.create_index(
        "ix_opportunities_external",
        "opportunities",
        ["organization_id", "external_source", "external_id"],
    )

    op.create_table(
        "opportunity_sources",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", enum_string(40), nullable=False),
        sa.Column("source_url", sa.String(2000)),
        sa.Column("original_filename", sa.String(500)),
        sa.Column("mime_type", sa.String(255)),
        sa.Column("raw_text", sa.Text()),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("external_source", sa.String(150)),
        sa.Column("external_id", sa.String(300)),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_sources_organization_id", "opportunity_sources", ["organization_id"]
    )
    op.create_index(
        "ix_opportunity_sources_opportunity_id", "opportunity_sources", ["opportunity_id"]
    )
    op.create_index(
        "ix_opportunity_sources_org_opportunity",
        "opportunity_sources",
        ["organization_id", "opportunity_id"],
    )

    op.create_table(
        "opportunity_analyses",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", enum_string(40), nullable=False),
        sa.Column("model_name", sa.String(150)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("source_snapshot", sa.Text()),
        sa.Column("extracted_summary", sa.Text()),
        sa.Column("extracted_metadata", sa.JSON()),
        sa.Column("error_message", sa.Text()),
        sa.Column("readiness_score", sa.Float()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_analyses_organization_id", "opportunity_analyses", ["organization_id"]
    )
    op.create_index(
        "ix_opportunity_analyses_opportunity_id", "opportunity_analyses", ["opportunity_id"]
    )
    op.create_index(
        "ix_opportunity_analyses_org_opportunity",
        "opportunity_analyses",
        ["organization_id", "opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_analyses_status", "opportunity_analyses", ["organization_id", "status"]
    )

    op.create_table(
        "opportunity_roles",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["opportunity_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_roles_organization_id", "opportunity_roles", ["organization_id"]
    )
    op.create_index(
        "ix_opportunity_roles_org_analysis", "opportunity_roles", ["organization_id", "analysis_id"]
    )
    op.create_index(
        "ix_opportunity_roles_org_title", "opportunity_roles", ["organization_id", "title"]
    )

    op.create_table(
        "opportunity_requirements",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_type", enum_string(50), nullable=False),
        sa.Column("importance", enum_string(30), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("normalized_value", sa.String(500)),
        sa.Column("values_json", sa.JSON()),
        sa.Column("minimum_years", sa.Float()),
        sa.Column("minimum_count", sa.Integer()),
        sa.Column("minimum_degree_level", sa.String(50)),
        sa.Column("operator", sa.String(30), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("evidence_required", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("source_excerpt", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["opportunity_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["opportunity_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_requirements_organization_id",
        "opportunity_requirements",
        ["organization_id"],
    )
    op.create_index(
        "ix_opportunity_requirements_org_role",
        "opportunity_requirements",
        ["organization_id", "role_id"],
    )
    op.create_index(
        "ix_opportunity_requirements_org_type",
        "opportunity_requirements",
        ["organization_id", "requirement_type"],
    )

    op.create_table(
        "team_requirements",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_type", enum_string(50), nullable=False),
        sa.Column("importance", enum_string(30), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("normalized_value", sa.String(500)),
        sa.Column("values_json", sa.JSON()),
        sa.Column("minimum_count", sa.Integer()),
        sa.Column("minimum_years", sa.Float()),
        sa.Column("operator", sa.String(30), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("source_excerpt", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["opportunity_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_team_requirements_organization_id", "team_requirements", ["organization_id"]
    )
    op.create_index(
        "ix_team_requirements_org_analysis", "team_requirements", ["organization_id", "analysis_id"]
    )

    op.create_table(
        "candidate_matches",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("mandatory_pass_rate", sa.Float(), nullable=False),
        sa.Column("preferred_pass_rate", sa.Float(), nullable=False),
        sa.Column("mandatory_failed", sa.Boolean(), nullable=False),
        sa.Column("rank", sa.Integer()),
        sa.Column("explanation", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["opportunity_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["opportunity_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_matches_organization_id", "candidate_matches", ["organization_id"]
    )
    op.create_index(
        "ix_candidate_matches_org_role_score",
        "candidate_matches",
        ["organization_id", "role_id", "score"],
    )
    op.create_index(
        "ix_candidate_matches_org_person", "candidate_matches", ["organization_id", "person_id"]
    )

    op.create_table(
        "requirement_matches",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_match_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("status", enum_string(30), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("evidence_json", sa.JSON()),
        sa.Column("explanation", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_match_id"], ["candidate_matches.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["opportunity_requirements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_requirement_matches_organization_id", "requirement_matches", ["organization_id"]
    )
    op.create_index(
        "ix_requirement_matches_org_candidate",
        "requirement_matches",
        ["organization_id", "candidate_match_id"],
    )

    op.create_table(
        "recommended_teams",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", enum_string(30), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("mandatory_constraints_satisfied", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["opportunity_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommended_teams_organization_id", "recommended_teams", ["organization_id"]
    )
    op.create_index(
        "ix_recommended_teams_org_analysis_score",
        "recommended_teams",
        ["organization_id", "analysis_id", "score"],
    )

    op.create_table(
        "recommended_team_members",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_match_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_score", sa.Float(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["recommended_teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["opportunity_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_match_id"], ["candidate_matches.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommended_team_members_organization_id",
        "recommended_team_members",
        ["organization_id"],
    )
    op.create_index(
        "ix_recommended_team_members_org_team",
        "recommended_team_members",
        ["organization_id", "team_id"],
    )

    op.create_table(
        "capability_gaps",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid()),
        sa.Column("requirement_id", sa.Uuid()),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("best_candidate_person_id", sa.Uuid()),
        sa.Column("best_candidate_score", sa.Float()),
        sa.Column("recommendation", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["opportunity_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["opportunity_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["opportunity_requirements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["best_candidate_person_id"], ["people.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capability_gaps_organization_id", "capability_gaps", ["organization_id"])
    op.create_index(
        "ix_capability_gaps_org_analysis", "capability_gaps", ["organization_id", "analysis_id"]
    )


def downgrade() -> None:
    for table in (
        "capability_gaps",
        "recommended_team_members",
        "recommended_teams",
        "requirement_matches",
        "candidate_matches",
        "team_requirements",
        "opportunity_requirements",
        "opportunity_roles",
        "opportunity_analyses",
        "opportunity_sources",
        "opportunities",
    ):
        op.drop_table(table)
