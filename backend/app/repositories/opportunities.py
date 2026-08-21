import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import (
    CandidateMatch,
    CapabilityGap,
    Opportunity,
    OpportunityAnalysis,
    OpportunityRequirement,
    OpportunityRole,
    RecommendedTeam,
    RecommendedTeamMember,
    RequirementMatch,
    TeamRequirement,
)


class OpportunityRepository:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    async def list_opportunities(self) -> list[Opportunity]:
        rows = await self.session.scalars(
            select(Opportunity)
            .where(Opportunity.organization_id == self.organization_id)
            .order_by(Opportunity.updated_at.desc())
        )
        return list(rows)

    async def get(self, opportunity_id: uuid.UUID) -> Opportunity | None:
        rows = await self.session.scalars(
            select(Opportunity).where(
                Opportunity.id == opportunity_id,
                Opportunity.organization_id == self.organization_id,
            )
        )
        return rows.first()

    async def next_analysis_version(self, opportunity_id: uuid.UUID) -> int:
        current = await self.session.scalar(
            select(func.max(OpportunityAnalysis.version)).where(
                OpportunityAnalysis.opportunity_id == opportunity_id,
                OpportunityAnalysis.organization_id == self.organization_id,
            )
        )
        return int(current or 0) + 1

    async def latest_analysis(self, opportunity_id: uuid.UUID) -> OpportunityAnalysis | None:
        rows = await self.session.scalars(
            select(OpportunityAnalysis)
            .where(
                OpportunityAnalysis.opportunity_id == opportunity_id,
                OpportunityAnalysis.organization_id == self.organization_id,
            )
            .order_by(OpportunityAnalysis.version.desc())
        )
        return rows.first()

    async def roles(self, analysis_id: uuid.UUID) -> list[OpportunityRole]:
        rows = await self.session.scalars(
            select(OpportunityRole)
            .where(
                OpportunityRole.analysis_id == analysis_id,
                OpportunityRole.organization_id == self.organization_id,
            )
            .order_by(OpportunityRole.sort_order, OpportunityRole.title)
        )
        return list(rows)

    async def requirements(self, role_id: uuid.UUID) -> list[OpportunityRequirement]:
        rows = await self.session.scalars(
            select(OpportunityRequirement).where(
                OpportunityRequirement.role_id == role_id,
                OpportunityRequirement.organization_id == self.organization_id,
            )
        )
        return list(rows)

    async def team_requirements(self, analysis_id: uuid.UUID) -> list[TeamRequirement]:
        rows = await self.session.scalars(
            select(TeamRequirement).where(
                TeamRequirement.analysis_id == analysis_id,
                TeamRequirement.organization_id == self.organization_id,
            )
        )
        return list(rows)

    async def candidate_matches(self, role_id: uuid.UUID) -> list[CandidateMatch]:
        rows = await self.session.scalars(
            select(CandidateMatch)
            .where(
                CandidateMatch.role_id == role_id,
                CandidateMatch.organization_id == self.organization_id,
            )
            .order_by(CandidateMatch.rank.asc().nullslast(), CandidateMatch.score.desc())
        )
        return list(rows)

    async def requirement_matches(self, candidate_match_id: uuid.UUID) -> list[RequirementMatch]:
        rows = await self.session.scalars(
            select(RequirementMatch).where(
                RequirementMatch.candidate_match_id == candidate_match_id,
                RequirementMatch.organization_id == self.organization_id,
            )
        )
        return list(rows)

    async def teams(self, analysis_id: uuid.UUID) -> list[RecommendedTeam]:
        rows = await self.session.scalars(
            select(RecommendedTeam)
            .where(
                RecommendedTeam.analysis_id == analysis_id,
                RecommendedTeam.organization_id == self.organization_id,
            )
            .order_by(RecommendedTeam.score.desc())
        )
        return list(rows)

    async def team_members(self, team_id: uuid.UUID) -> list[RecommendedTeamMember]:
        rows = await self.session.scalars(
            select(RecommendedTeamMember).where(
                RecommendedTeamMember.team_id == team_id,
                RecommendedTeamMember.organization_id == self.organization_id,
            )
        )
        return list(rows)

    async def gaps(self, analysis_id: uuid.UUID) -> list[CapabilityGap]:
        rows = await self.session.scalars(
            select(CapabilityGap).where(
                CapabilityGap.analysis_id == analysis_id,
                CapabilityGap.organization_id == self.organization_id,
            )
        )
        return list(rows)

    def add(self, model: object) -> None:
        self.session.add(model)
