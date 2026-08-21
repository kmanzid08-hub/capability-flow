import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.opportunity_config import get_opportunity_intelligence_settings
from app.models.opportunity import (
    CandidateMatch,
    CapabilityGap,
    Opportunity,
    OpportunityAnalysis,
    OpportunityRequirement,
    OpportunityRole,
    OpportunitySource,
    RecommendedTeam,
    RecommendedTeamMember,
    RequirementMatch,
    TeamRequirement,
)
from app.models.opportunity_enums import (
    AnalysisStatus,
    MatchStatus,
    OpportunitySourceType,
    OpportunityStatus,
    RequirementImportance,
    TeamStatus,
)
from app.repositories.opportunities import OpportunityRepository
from app.schemas.opportunity import ExtractedOpportunity, OpportunityCreate, OpportunityUpdate
from app.services.matching import CandidateEvaluation, MatchingEngine, PersonProfile
from app.services.opportunity_metadata import suggest_metadata
from app.services.opportunity_source_storage import OpportunitySourceStorage
from app.services.requirement_extraction import ClaudeRequirementExtractor
from app.services.source_ingestion import OpportunitySourceIngestionService
from app.services.team_optimizer import RoleCandidateSet, TeamAssignment, TeamOptimizer


class OpportunityService:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id
        self.user_id = user_id
        self.repo = OpportunityRepository(session, organization_id)
        self.ingestion = OpportunitySourceIngestionService()
        self.source_storage = OpportunitySourceStorage()
        self.matching = MatchingEngine(session, organization_id)
        self.optimizer = TeamOptimizer()
        self.settings = get_opportunity_intelligence_settings()

    async def list_opportunities(self) -> list[Opportunity]:
        return await self.repo.list_opportunities()

    async def get(self, opportunity_id: uuid.UUID) -> Opportunity:
        item = await self.repo.get(opportunity_id)
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity not found")
        return item

    async def create(self, data: OpportunityCreate) -> Opportunity:
        item = Opportunity(
            organization_id=self.organization_id,
            title=data.title,
            client_name=data.client_name,
            reference_number=data.reference_number,
            description=data.description,
            source_url=str(data.source_url) if data.source_url else None,
            deadline_at=data.deadline_at,
            external_source=data.external_source,
            external_id=data.external_id,
            internal_notes=data.internal_notes,
            created_by_user_id=self.user_id,
            updated_by_user_id=self.user_id,
        )
        self.repo.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update(
        self,
        opportunity_id: uuid.UUID,
        data: OpportunityUpdate,
    ) -> Opportunity:
        item = await self.get(opportunity_id)
        values = data.model_dump(exclude_unset=True)

        requested_status = values.pop("status", None)
        if "source_url" in values and values["source_url"] is not None:
            values["source_url"] = str(values["source_url"])

        for field, value in values.items():
            setattr(item, field, value)

        if requested_status is not None and requested_status != item.status:
            self._apply_status_transition(item, requested_status)

        item.updated_by_user_id = self.user_id
        await self.session.commit()
        await self.session.refresh(item)
        return item

    def _apply_status_transition(
        self,
        item: Opportunity,
        target: OpportunityStatus,
    ) -> None:
        allowed: dict[OpportunityStatus, set[OpportunityStatus]] = {
            OpportunityStatus.NEW: {
                OpportunityStatus.NEEDS_REVIEW,
                OpportunityStatus.READY,
                OpportunityStatus.ARCHIVED,
            },
            OpportunityStatus.ANALYZING: {
                OpportunityStatus.NEEDS_REVIEW,
                OpportunityStatus.READY,
            },
            OpportunityStatus.NEEDS_REVIEW: {
                OpportunityStatus.READY,
                OpportunityStatus.NOT_PURSUING,
                OpportunityStatus.ARCHIVED,
            },
            OpportunityStatus.READY: {
                OpportunityStatus.PURSUING,
                OpportunityStatus.NOT_PURSUING,
                OpportunityStatus.ARCHIVED,
            },
            OpportunityStatus.PURSUING: {
                OpportunityStatus.READY,
                OpportunityStatus.SUBMITTED,
                OpportunityStatus.NOT_PURSUING,
                OpportunityStatus.ARCHIVED,
            },
            OpportunityStatus.SUBMITTED: {
                OpportunityStatus.PURSUING,
                OpportunityStatus.WON,
                OpportunityStatus.LOST,
                OpportunityStatus.ARCHIVED,
            },
            OpportunityStatus.WON: {
                OpportunityStatus.ARCHIVED,
            },
            OpportunityStatus.LOST: {
                OpportunityStatus.PURSUING,
                OpportunityStatus.ARCHIVED,
            },
            OpportunityStatus.NOT_PURSUING: {
                OpportunityStatus.READY,
                OpportunityStatus.PURSUING,
                OpportunityStatus.ARCHIVED,
            },
            OpportunityStatus.ARCHIVED: set(),
        }

        if target not in allowed[item.status]:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Cannot move opportunity from {item.status.value} to {target.value}",
            )

        now = datetime.now(UTC)

        if target in {
            OpportunityStatus.PURSUING,
            OpportunityStatus.NOT_PURSUING,
        }:
            item.decision_at = now
            item.decision_by_user_id = self.user_id

        if target == OpportunityStatus.SUBMITTED:
            if item.selected_team_id is None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Select a team before marking the opportunity submitted",
                )
            if item.decision_at is None:
                item.decision_at = now
                item.decision_by_user_id = self.user_id
            item.submitted_at = now
            item.submitted_by_user_id = self.user_id

        if target in {
            OpportunityStatus.WON,
            OpportunityStatus.LOST,
        }:
            if item.submitted_at is None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "An opportunity must be submitted before recording an outcome",
                )
            item.outcome_at = now
            item.outcome_by_user_id = self.user_id

        item.status = target

    async def select_team(
        self,
        opportunity_id: uuid.UUID,
        team_id: uuid.UUID,
    ) -> Opportunity:
        item = await self.get(opportunity_id)

        if item.status not in {
            OpportunityStatus.READY,
            OpportunityStatus.PURSUING,
        }:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "A team can only be selected while an opportunity is ready or pursuing",
            )

        analysis = await self.analysis(opportunity_id)
        team = await self.session.scalar(
            select(RecommendedTeam).where(
                RecommendedTeam.id == team_id,
                RecommendedTeam.analysis_id == analysis.id,
                RecommendedTeam.opportunity_id == opportunity_id,
                RecommendedTeam.organization_id == self.organization_id,
            )
        )
        if team is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommended team not found")

        if item.selected_team_id and item.selected_team_id != team.id:
            previous = await self.session.scalar(
                select(RecommendedTeam).where(
                    RecommendedTeam.id == item.selected_team_id,
                    RecommendedTeam.organization_id == self.organization_id,
                )
            )
            if previous is not None:
                previous.status = TeamStatus.RECOMMENDED

        team.status = TeamStatus.SELECTED
        item.selected_team_id = team.id
        item.selected_team_at = datetime.now(UTC)
        item.selected_team_by_user_id = self.user_id
        item.updated_by_user_id = self.user_id

        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def sources(self, opportunity_id: uuid.UUID) -> list[OpportunitySource]:
        await self.get(opportunity_id)
        return list(
            await self.session.scalars(
                select(OpportunitySource)
                .where(
                    OpportunitySource.opportunity_id == opportunity_id,
                    OpportunitySource.organization_id == self.organization_id,
                )
                .order_by(OpportunitySource.created_at.desc())
            )
        )

    async def source(
        self,
        opportunity_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> OpportunitySource:
        await self.get(opportunity_id)
        source = await self.session.scalar(
            select(OpportunitySource).where(
                OpportunitySource.id == source_id,
                OpportunitySource.opportunity_id == opportunity_id,
                OpportunitySource.organization_id == self.organization_id,
            )
        )
        if source is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Opportunity source not found")
        return source

    async def delete_source(
        self,
        opportunity_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> None:
        source = await self.source(opportunity_id, source_id)
        self.source_storage.delete(source.storage_path)
        await self.session.delete(source)
        await self.session.commit()

    async def _existing_source_by_hash(
        self,
        opportunity_id: uuid.UUID,
        content_hash: str,
    ) -> OpportunitySource | None:
        source: OpportunitySource | None = await self.session.scalar(
            select(OpportunitySource).where(
                OpportunitySource.opportunity_id == opportunity_id,
                OpportunitySource.organization_id == self.organization_id,
                OpportunitySource.content_hash == content_hash,
            )
        )
        return source

    def _apply_source_metadata(
        self,
        opportunity: Opportunity,
        source: OpportunitySource,
    ) -> None:
        metadata = source.metadata_json or {}
        suggestion = suggest_metadata(
            source.raw_text or "",
            page_title=str(metadata.get("page_title")) if metadata.get("page_title") else None,
            filename=source.original_filename,
        )
        if opportunity.title.strip().lower() in {"untitled opportunity", "new opportunity"}:
            if suggestion.title:
                opportunity.title = suggestion.title
        if opportunity.reference_number is None and suggestion.reference_number:
            opportunity.reference_number = suggestion.reference_number
        if opportunity.deadline_at is None and suggestion.deadline_at:
            opportunity.deadline_at = suggestion.deadline_at
        if opportunity.description is None and source.raw_text:
            opportunity.description = source.raw_text[:4000]
        opportunity.updated_by_user_id = self.user_id

    async def add_text_source(
        self,
        opportunity_id: uuid.UUID,
        text: str,
        source_type: OpportunitySourceType = OpportunitySourceType.PASTED_TEXT,
        source_url: str | None = None,
    ) -> OpportunitySource:
        opportunity = await self.get(opportunity_id)
        ingested = self.ingestion._finish(text, "text/plain")
        existing = await self._existing_source_by_hash(opportunity_id, ingested.content_hash)
        if existing is not None:
            return existing
        source = OpportunitySource(
            organization_id=self.organization_id,
            opportunity_id=opportunity_id,
            source_type=source_type,
            source_url=source_url,
            raw_text=ingested.text,
            content_hash=ingested.content_hash,
            mime_type=ingested.mime_type,
            metadata_json=ingested.metadata,
            created_by_user_id=self.user_id,
        )
        self.repo.add(source)
        self._apply_source_metadata(opportunity, source)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def add_url_source(self, opportunity_id: uuid.UUID, url: str) -> OpportunitySource:
        opportunity = await self.get(opportunity_id)
        ingested = await self.ingestion.from_url(url)
        existing = await self._existing_source_by_hash(opportunity_id, ingested.content_hash)
        if existing is not None:
            return existing

        # Pilot mode: keep fetched source text and metadata in PostgreSQL.
        # Do not persist URL snapshots to the web service filesystem.
        stored_filename = None
        storage_path = None

        source = OpportunitySource(
            organization_id=self.organization_id,
            opportunity_id=opportunity_id,
            source_type=OpportunitySourceType.URL,
            source_url=url,
            original_filename=ingested.suggested_filename,
            stored_filename=stored_filename,
            storage_path=storage_path,
            file_size=None,
            raw_text=ingested.text,
            content_hash=ingested.content_hash,
            mime_type=ingested.mime_type,
            metadata_json=ingested.metadata,
            created_by_user_id=self.user_id,
        )
        self.repo.add(source)
        if opportunity.source_url is None:
            opportunity.source_url = url
        self._apply_source_metadata(opportunity, source)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def add_file_source(
        self,
        opportunity_id: uuid.UUID,
        content: bytes,
        filename: str,
        mime_type: str | None,
    ) -> OpportunitySource:
        opportunity = await self.get(opportunity_id)
        ingested = self.ingestion.from_bytes(content, filename, mime_type)
        existing = await self._existing_source_by_hash(opportunity_id, ingested.content_hash)
        if existing is not None:
            return existing
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "other"
        source_type = {
            "pdf": OpportunitySourceType.PDF,
            "docx": OpportunitySourceType.DOCX,
            "xlsx": OpportunitySourceType.XLSX,
            "xlsm": OpportunitySourceType.XLSX,
            "pptx": OpportunitySourceType.PPTX,
        }.get(suffix, OpportunitySourceType.OTHER)
        stored_filename, storage_path = self.source_storage.store(
            organization_id=self.organization_id,
            opportunity_id=opportunity_id,
            content=content,
            filename=filename,
        )
        source = OpportunitySource(
            organization_id=self.organization_id,
            opportunity_id=opportunity_id,
            source_type=source_type,
            original_filename=filename,
            stored_filename=stored_filename,
            storage_path=storage_path,
            file_size=len(content),
            mime_type=mime_type or ingested.mime_type,
            raw_text=ingested.text,
            content_hash=ingested.content_hash,
            metadata_json=ingested.metadata,
            created_by_user_id=self.user_id,
        )
        self.repo.add(source)
        self._apply_source_metadata(opportunity, source)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def analyze(self, opportunity_id: uuid.UUID) -> OpportunityAnalysis:
        opportunity = await self.get(opportunity_id)
        workflow_status = opportunity.status
        workflow_locked = workflow_status in {
            OpportunityStatus.PURSUING,
            OpportunityStatus.NOT_PURSUING,
            OpportunityStatus.SUBMITTED,
            OpportunityStatus.WON,
            OpportunityStatus.LOST,
            OpportunityStatus.ARCHIVED,
        }
        sources = list(
            await self.session.scalars(
                select(OpportunitySource)
                .where(
                    OpportunitySource.opportunity_id == opportunity_id,
                    OpportunitySource.organization_id == self.organization_id,
                )
                .order_by(OpportunitySource.created_at)
            )
        )
        source_text = "\n\n".join(source.raw_text or "" for source in sources).strip()
        if not source_text:
            if opportunity.description:
                source_text = opportunity.description
            else:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Add a readable source before analysis",
                )
        version = await self.repo.next_analysis_version(opportunity_id)
        analysis = OpportunityAnalysis(
            organization_id=self.organization_id,
            opportunity_id=opportunity_id,
            version=version,
            status=AnalysisStatus.ANALYZING,
            model_name=self.settings.anthropic_model,
            started_at=datetime.now(UTC),
            source_snapshot=source_text,
            created_by_user_id=self.user_id,
        )
        self.repo.add(analysis)
        if not workflow_locked:
            opportunity.status = OpportunityStatus.ANALYZING
        await self.session.commit()
        await self.session.refresh(analysis)
        try:
            extracted = await ClaudeRequirementExtractor().extract(source_text)
            await self._persist_extracted(opportunity, analysis, extracted)
            analysis.status = AnalysisStatus.MATCHING
            await self.session.commit()
            await self._run_matching(opportunity, analysis)
            analysis.status = AnalysisStatus.COMPLETE
            analysis.completed_at = datetime.now(UTC)
            if not workflow_locked:
                opportunity.status = OpportunityStatus.READY
            await self.session.commit()
            await self.session.refresh(analysis)
            return analysis
        except Exception as exc:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(exc)
            analysis.completed_at = datetime.now(UTC)
            if not workflow_locked:
                opportunity.status = OpportunityStatus.NEEDS_REVIEW
            await self.session.commit()
            raise

    async def _persist_extracted(
        self,
        opportunity: Opportunity,
        analysis: OpportunityAnalysis,
        extracted: ExtractedOpportunity,
    ) -> None:
        analysis.extracted_summary = extracted.summary
        analysis.extracted_metadata = extracted.model_dump(mode="json")
        if extracted.title and (
            not opportunity.title or opportunity.title.lower().startswith("untitled")
        ):
            opportunity.title = extracted.title
        if extracted.client_name and not opportunity.client_name:
            opportunity.client_name = extracted.client_name
        if extracted.reference_number and not opportunity.reference_number:
            opportunity.reference_number = extracted.reference_number
        if extracted.deadline_at and not opportunity.deadline_at:
            opportunity.deadline_at = extracted.deadline_at
        for index, role_data in enumerate(extracted.roles):
            role = OpportunityRole(
                organization_id=self.organization_id,
                opportunity_id=opportunity.id,
                analysis_id=analysis.id,
                title=role_data.title,
                description=role_data.description,
                quantity=role_data.quantity,
                is_mandatory=role_data.is_mandatory,
                sort_order=index,
            )
            self.repo.add(role)
            await self.session.flush()
            for requirement_data in role_data.requirements:
                self.repo.add(
                    OpportunityRequirement(
                        organization_id=self.organization_id,
                        opportunity_id=opportunity.id,
                        analysis_id=analysis.id,
                        role_id=role.id,
                        requirement_type=requirement_data.requirement_type,
                        importance=requirement_data.importance,
                        label=requirement_data.label,
                        normalized_value=requirement_data.normalized_value,
                        values_json=requirement_data.values,
                        minimum_years=requirement_data.minimum_years,
                        minimum_count=requirement_data.minimum_count,
                        minimum_degree_level=requirement_data.minimum_degree_level,
                        operator=requirement_data.operator,
                        weight=requirement_data.weight,
                        evidence_required=requirement_data.evidence_required,
                        notes=requirement_data.notes,
                        source_excerpt=requirement_data.source_excerpt,
                    )
                )
        for team_req in extracted.team_requirements:
            self.repo.add(
                TeamRequirement(
                    organization_id=self.organization_id,
                    opportunity_id=opportunity.id,
                    analysis_id=analysis.id,
                    requirement_type=team_req.requirement_type,
                    importance=team_req.importance,
                    label=team_req.label,
                    normalized_value=team_req.normalized_value,
                    values_json=team_req.values,
                    minimum_count=team_req.minimum_count,
                    minimum_years=team_req.minimum_years,
                    operator=team_req.operator,
                    weight=team_req.weight,
                    source_excerpt=team_req.source_excerpt,
                )
            )
        await self.session.commit()

    async def _run_matching(self, opportunity: Opportunity, analysis: OpportunityAnalysis) -> None:
        profiles = await self.matching.load_profiles()
        roles = await self.repo.roles(analysis.id)
        role_sets: list[RoleCandidateSet] = []
        top_scores: list[float] = []
        for role in roles:
            requirements = await self.repo.requirements(role.id)
            evaluations = [self.matching.evaluate(profile, requirements) for profile in profiles]
            evaluations.sort(key=lambda item: (not item.mandatory_failed, item.score), reverse=True)
            evaluations = evaluations[: self.settings.opportunity_max_candidates_per_role]
            persisted: list[tuple[CandidateMatch, CandidateEvaluation]] = []
            for rank, evaluation in enumerate(evaluations, start=1):
                match = CandidateMatch(
                    organization_id=self.organization_id,
                    opportunity_id=opportunity.id,
                    analysis_id=analysis.id,
                    role_id=role.id,
                    person_id=evaluation.person.id,
                    score=evaluation.score,
                    mandatory_pass_rate=evaluation.mandatory_pass_rate,
                    preferred_pass_rate=evaluation.preferred_pass_rate,
                    mandatory_failed=evaluation.mandatory_failed,
                    rank=rank,
                    explanation=(
                        "All mandatory requirements satisfied."
                        if not evaluation.mandatory_failed
                        else "One or more mandatory requirements are not fully satisfied."
                    ),
                )
                self.repo.add(match)
                await self.session.flush()
                for requirement in requirements:
                    result = evaluation.requirement_results[requirement.id]
                    self.repo.add(
                        RequirementMatch(
                            organization_id=self.organization_id,
                            candidate_match_id=match.id,
                            requirement_id=requirement.id,
                            status=result.status,
                            score=result.score,
                            evidence_json=[item.as_json() for item in result.evidence],
                            explanation=result.explanation,
                        )
                    )
                persisted.append((match, evaluation))
            if persisted:
                top_scores.append(float(persisted[0][0].score))
            role_sets.append(
                RoleCandidateSet(
                    role.id,
                    role.title,
                    role.quantity,
                    [item[1] for item in persisted],
                )
            )
        await self.session.commit()
        analysis.status = AnalysisStatus.BUILDING_TEAM
        await self.session.commit()
        options = self.optimizer.build(role_sets, self.settings.opportunity_default_team_options)
        team_requirements = await self.repo.team_requirements(analysis.id)
        profiles_by_person = {profile.person.id: profile for profile in profiles}
        for index, option in enumerate(options, start=1):
            team_constraints_ok = self._team_constraints_satisfied(
                option.assignments, team_requirements, profiles_by_person
            )
            effective_score = option.score if team_constraints_ok else min(option.score, 79.0)
            team = RecommendedTeam(
                organization_id=self.organization_id,
                opportunity_id=opportunity.id,
                analysis_id=analysis.id,
                name=f"Recommended Team {index}",
                score=effective_score,
                mandatory_constraints_satisfied=(
                    option.mandatory_constraints_satisfied and team_constraints_ok
                ),
                explanation=(
                    "Assigned members satisfy role-level and team-level mandatory requirements."
                    if option.mandatory_constraints_satisfied and team_constraints_ok
                    else (
                        "Best available combination includes at least one mandatory role "
                        "or team-level gap."
                    )
                ),
            )
            self.repo.add(team)
            await self.session.flush()
            for assignment in option.assignments:
                candidate_match = await self.session.scalar(
                    select(CandidateMatch).where(
                        CandidateMatch.analysis_id == analysis.id,
                        CandidateMatch.role_id == assignment.role_id,
                        CandidateMatch.person_id == assignment.candidate.person.id,
                    )
                )

                if candidate_match is None:
                    continue

                self.repo.add(
                    RecommendedTeamMember(
                        organization_id=self.organization_id,
                        team_id=team.id,
                        role_id=assignment.role_id,
                        person_id=assignment.candidate.person.id,
                        candidate_match_id=candidate_match.id,
                        assignment_score=assignment.candidate.score,
                    )
                )
        for role in roles:
            matches = await self.repo.candidate_matches(role.id)
            best: CandidateMatch | None = matches[0] if matches else None
            if best is None or best.mandatory_failed:
                self.repo.add(
                    CapabilityGap(
                        organization_id=self.organization_id,
                        opportunity_id=opportunity.id,
                        analysis_id=analysis.id,
                        role_id=role.id,
                        severity="critical" if role.is_mandatory else "warning",
                        label=f"No fully compliant internal candidate for {role.title}",
                        best_candidate_person_id=best.person_id if best else None,
                        best_candidate_score=best.score if best else None,
                        recommendation=(
                            "Review external recruitment, subcontracting, or partner capability."
                        ),
                    )
                )
        analysis.readiness_score = (
            round(sum(top_scores) / len(top_scores), 2) if top_scores else 0.0
        )
        await self.session.commit()

    def _team_constraints_satisfied(
        self,
        assignments: list[TeamAssignment],
        requirements: list[TeamRequirement],
        profiles_by_person: dict[uuid.UUID, PersonProfile],
    ) -> bool:
        for requirement in requirements:
            if requirement.importance != RequirementImportance.MANDATORY:
                continue
            proxy = SimpleNamespace(
                id=uuid.uuid4(),
                requirement_type=requirement.requirement_type,
                importance=requirement.importance,
                label=requirement.label,
                normalized_value=requirement.normalized_value,
                values_json=requirement.values_json,
                minimum_years=requirement.minimum_years,
                minimum_count=None,
                minimum_degree_level=None,
                operator=requirement.operator,
                weight=requirement.weight,
                evidence_required=False,
            )
            matched_count = 0
            for assignment in assignments:
                profile = profiles_by_person.get(assignment.candidate.person.id)
                if profile is None:
                    continue
                result = self.matching.evaluate_requirement(profile, proxy)
                if result.status == MatchStatus.MATCHED or (
                    result.status == MatchStatus.PARTIAL and result.score >= 0.75
                ):
                    matched_count += 1
            needed = requirement.minimum_count or 1
            if matched_count < needed:
                return False
        return True

    async def analysis(self, opportunity_id: uuid.UUID) -> OpportunityAnalysis:
        await self.get(opportunity_id)
        item = await self.repo.latest_analysis(opportunity_id)
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No analysis found")
        return item

    async def analysis_roles(self, opportunity_id: uuid.UUID) -> list[OpportunityRole]:
        analysis = await self.analysis(opportunity_id)
        return await self.repo.roles(analysis.id)

    async def role_matches(
        self,
        opportunity_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> list[CandidateMatch]:
        analysis = await self.analysis(opportunity_id)
        role = await self.session.scalar(
            select(OpportunityRole).where(
                OpportunityRole.id == role_id,
                OpportunityRole.analysis_id == analysis.id,
                OpportunityRole.organization_id == self.organization_id,
            )
        )
        if role is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
        return await self.repo.candidate_matches(role_id)

    async def teams(self, opportunity_id: uuid.UUID) -> list[RecommendedTeam]:
        analysis = await self.analysis(opportunity_id)
        return await self.repo.teams(analysis.id)

    async def gaps(self, opportunity_id: uuid.UUID) -> list[CapabilityGap]:
        analysis = await self.analysis(opportunity_id)
        return await self.repo.gaps(analysis.id)
