import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies import ActiveMembership, CurrentUser, SessionDep
from app.models.enums import MembershipRole
from app.models.opportunity import (
    CapabilityGap,
    Opportunity,
    OpportunityAnalysis,
    OpportunitySource,
)
from app.models.opportunity_enums import OpportunitySourceType
from app.models.person import Person
from app.schemas.opportunity import (
    AnalysisResponse,
    CandidateMatchResponse,
    CapabilityGapResponse,
    OpportunityCreate,
    OpportunityIntakeResponse,
    OpportunityResponse,
    OpportunitySourceResponse,
    OpportunityUpdate,
    RecommendedTeamMemberResponse,
    RecommendedTeamResponse,
    RequirementMatchResponse,
    RequirementResponse,
    RoleResponse,
    SourceTextCreate,
    SourceUrlCreate,
    TextIntakeCreate,
    UrlIntakeCreate,
)
from app.services.opportunities import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])
WRITE_ROLES = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
    MembershipRole.MANAGER,
    MembershipRole.DATA_ENTRY,
}
MANAGEMENT_ROLES = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
    MembershipRole.MANAGER,
}


def require_write_access(membership: ActiveMembership) -> None:
    if membership.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Write access is required")


def require_management_access(membership: ActiveMembership) -> None:
    if membership.role not in MANAGEMENT_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Management access is required")


def service(
    session: SessionDep,
    membership: ActiveMembership,
    user: CurrentUser,
) -> OpportunityService:
    return OpportunityService(session, membership.organization_id, user.id)


@router.get("", response_model=list[OpportunityResponse])
async def list_opportunities(
    membership: ActiveMembership, user: CurrentUser, session: SessionDep
) -> list[Opportunity]:
    return await service(session, membership, user).list_opportunities()


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    data: OpportunityCreate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Opportunity:
    require_write_access(membership)
    return await service(session, membership, user).create(data)


@router.post(
    "/intake/url",
    response_model=OpportunityIntakeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def intake_url(
    data: UrlIntakeCreate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> OpportunityIntakeResponse:
    require_write_access(membership)
    svc = service(session, membership, user)
    opportunity = await svc.create(
        OpportunityCreate(
            title=data.title or "Untitled opportunity",
            client_name=data.client_name,
            source_url=data.url,
        )
    )
    source = await svc.add_url_source(opportunity.id, str(data.url))
    await session.refresh(opportunity)
    return OpportunityIntakeResponse(
        opportunity=OpportunityResponse.model_validate(opportunity),
        source=OpportunitySourceResponse.model_validate(source),
    )


@router.post(
    "/intake/text",
    response_model=OpportunityIntakeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def intake_text(
    data: TextIntakeCreate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> OpportunityIntakeResponse:
    require_write_access(membership)
    svc = service(session, membership, user)
    opportunity = await svc.create(
        OpportunityCreate(
            title=data.title or "Untitled opportunity",
            client_name=data.client_name,
            source_url=data.source_url,
        )
    )
    source = await svc.add_text_source(
        opportunity.id,
        data.text,
        OpportunitySourceType.PASTED_TEXT,
        str(data.source_url) if data.source_url else None,
    )
    await session.refresh(opportunity)
    return OpportunityIntakeResponse(
        opportunity=OpportunityResponse.model_validate(opportunity),
        source=OpportunitySourceResponse.model_validate(source),
    )


@router.post(
    "/intake/file",
    response_model=OpportunityIntakeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def intake_file(
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    client_name: Annotated[str | None, Form()] = None,
) -> OpportunityIntakeResponse:
    require_write_access(membership)
    content = await file.read()
    svc = service(session, membership, user)
    opportunity = await svc.create(
        OpportunityCreate(
            title=title or "Untitled opportunity",
            client_name=client_name,
        )
    )
    source = await svc.add_file_source(
        opportunity.id,
        content,
        file.filename or "source",
        file.content_type,
    )
    await session.refresh(opportunity)
    return OpportunityIntakeResponse(
        opportunity=OpportunityResponse.model_validate(opportunity),
        source=OpportunitySourceResponse.model_validate(source),
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Opportunity:
    return await service(session, membership, user).get(opportunity_id)


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: uuid.UUID,
    data: OpportunityUpdate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Opportunity:
    if data.status is not None:
        require_management_access(membership)
    else:
        require_write_access(membership)
    return await service(session, membership, user).update(opportunity_id, data)


@router.post(
    "/{opportunity_id}/teams/{team_id}/select",
    response_model=OpportunityResponse,
)
async def select_team(
    opportunity_id: uuid.UUID,
    team_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Opportunity:
    require_management_access(membership)
    return await service(session, membership, user).select_team(opportunity_id, team_id)


@router.post("/{opportunity_id}/sources/text", status_code=status.HTTP_201_CREATED)
async def add_text_source(
    opportunity_id: uuid.UUID,
    data: SourceTextCreate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> dict[str, str]:
    require_write_access(membership)
    source = await service(session, membership, user).add_text_source(
        opportunity_id,
        data.text,
        data.source_type,
        str(data.source_url) if data.source_url else None,
    )
    return {"id": str(source.id), "status": "stored"}


@router.post("/{opportunity_id}/sources/url", status_code=status.HTTP_201_CREATED)
async def add_url_source(
    opportunity_id: uuid.UUID,
    data: SourceUrlCreate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> dict[str, str]:
    require_write_access(membership)
    source = await service(session, membership, user).add_url_source(opportunity_id, str(data.url))
    return {"id": str(source.id), "status": "stored"}


@router.post("/{opportunity_id}/sources/file", status_code=status.HTTP_201_CREATED)
async def add_file_source(
    opportunity_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
) -> dict[str, str]:
    require_write_access(membership)
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Opportunity document exceeds 25 MB")
    source = await service(session, membership, user).add_file_source(
        opportunity_id,
        content,
        file.filename or "source",
        file.content_type,
    )
    return {"id": str(source.id), "status": "stored"}


@router.get(
    "/{opportunity_id}/sources",
    response_model=list[OpportunitySourceResponse],
)
async def list_sources(
    opportunity_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> list[OpportunitySource]:
    return await service(session, membership, user).sources(opportunity_id)


@router.get("/{opportunity_id}/sources/{source_id}/download")
async def download_source(
    opportunity_id: uuid.UUID,
    source_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> FileResponse:
    svc = service(session, membership, user)
    source = await svc.source(opportunity_id, source_id)
    if not source.storage_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This source has no stored snapshot")
    path = svc.source_storage.resolve(source.storage_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored source snapshot is missing")
    return FileResponse(
        path,
        media_type=source.mime_type or "application/octet-stream",
        filename=source.original_filename or source.stored_filename or "source",
    )


@router.delete(
    "/{opportunity_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_source(
    opportunity_id: uuid.UUID,
    source_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> None:
    require_write_access(membership)
    await service(session, membership, user).delete_source(opportunity_id, source_id)


@router.post("/{opportunity_id}/analyze", response_model=AnalysisResponse)
async def analyze_opportunity(
    opportunity_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> OpportunityAnalysis:
    require_write_access(membership)
    return await service(session, membership, user).analyze(opportunity_id)


@router.get("/{opportunity_id}/analysis", response_model=AnalysisResponse)
async def latest_analysis(
    opportunity_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> OpportunityAnalysis:
    return await service(session, membership, user).analysis(opportunity_id)


@router.get("/{opportunity_id}/roles", response_model=list[RoleResponse])
async def roles(
    opportunity_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> list[RoleResponse]:
    svc = service(session, membership, user)
    role_rows = await svc.analysis_roles(opportunity_id)
    output: list[RoleResponse] = []
    for role in role_rows:
        reqs = await svc.repo.requirements(role.id)
        output.append(
            RoleResponse(
                id=role.id,
                created_at=role.created_at,
                updated_at=role.updated_at,
                opportunity_id=role.opportunity_id,
                analysis_id=role.analysis_id,
                title=role.title,
                description=role.description,
                quantity=role.quantity,
                is_mandatory=role.is_mandatory,
                sort_order=role.sort_order,
                requirements=[RequirementResponse.model_validate(req) for req in reqs],
            )
        )
    return output


@router.get(
    "/{opportunity_id}/roles/{role_id}/matches",
    response_model=list[CandidateMatchResponse],
)
async def role_matches(
    opportunity_id: uuid.UUID,
    role_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> list[CandidateMatchResponse]:
    svc = service(session, membership, user)
    matches = await svc.role_matches(opportunity_id, role_id)
    output: list[CandidateMatchResponse] = []
    for match in matches:
        person = await session.get(Person, match.person_id)
        req_matches = await svc.repo.requirement_matches(match.id)
        output.append(
            CandidateMatchResponse(
                id=match.id,
                created_at=match.created_at,
                updated_at=match.updated_at,
                role_id=match.role_id,
                person_id=match.person_id,
                score=match.score,
                mandatory_pass_rate=match.mandatory_pass_rate,
                preferred_pass_rate=match.preferred_pass_rate,
                mandatory_failed=match.mandatory_failed,
                rank=match.rank,
                explanation=match.explanation,
                person_name=person.display_name if person else None,
                professional_title=person.professional_title if person else None,
                requirement_matches=[
                    RequirementMatchResponse.model_validate(item) for item in req_matches
                ],
            )
        )
    return output


@router.get("/{opportunity_id}/teams", response_model=list[RecommendedTeamResponse])
async def teams(
    opportunity_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> list[RecommendedTeamResponse]:
    svc = service(session, membership, user)
    team_rows = await svc.teams(opportunity_id)
    roles_by_id = {role.id: role for role in await svc.analysis_roles(opportunity_id)}
    output: list[RecommendedTeamResponse] = []
    for team in team_rows:
        members = await svc.repo.team_members(team.id)
        member_output: list[RecommendedTeamMemberResponse] = []
        for member in members:
            person = await session.get(Person, member.person_id)
            role = roles_by_id.get(member.role_id)
            member_output.append(
                RecommendedTeamMemberResponse(
                    id=member.id,
                    created_at=member.created_at,
                    updated_at=member.updated_at,
                    role_id=member.role_id,
                    person_id=member.person_id,
                    candidate_match_id=member.candidate_match_id,
                    assignment_score=member.assignment_score,
                    person_name=person.display_name if person else None,
                    role_title=role.title if role else None,
                )
            )
        output.append(
            RecommendedTeamResponse(
                id=team.id,
                created_at=team.created_at,
                updated_at=team.updated_at,
                analysis_id=team.analysis_id,
                name=team.name,
                status=team.status,
                score=team.score,
                mandatory_constraints_satisfied=team.mandatory_constraints_satisfied,
                explanation=team.explanation,
                members=member_output,
            )
        )
    return output


@router.get("/{opportunity_id}/gaps", response_model=list[CapabilityGapResponse])
async def gaps(
    opportunity_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> list[CapabilityGap]:
    return await service(session, membership, user).gaps(opportunity_id)
