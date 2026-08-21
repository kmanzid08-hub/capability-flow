import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import ActiveMembership, CurrentUser, SessionDep
from app.models.enums import MembershipRole
from app.models.profile_ai import ProfileSuggestion
from app.schemas.profile_ai import (
    AnalyzeDocumentResponse,
    ProfileCompletenessResponse,
    ProfileSuggestionResponse,
    SuggestionEdit,
)
from app.services.profile_ai import ProfileAIService

router = APIRouter(prefix="/people/{person_id}", tags=["profile-ai"])

ANALYZE_ROLES = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
    MembershipRole.MANAGER,
    MembershipRole.DATA_ENTRY,
}
REVIEW_ROLES = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
    MembershipRole.MANAGER,
    MembershipRole.REVIEWER,
}


def _service(
    session: SessionDep, membership: ActiveMembership, user: CurrentUser
) -> ProfileAIService:
    return ProfileAIService(session, membership.organization_id, user.id)


def _require(role: MembershipRole, allowed: set[MembershipRole]) -> None:
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This role cannot perform that action"
        )


@router.post("/documents/{document_id}/analyze", response_model=AnalyzeDocumentResponse)
async def analyze_document(
    person_id: uuid.UUID,
    document_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> AnalyzeDocumentResponse:
    _require(membership.role, ANALYZE_ROLES)
    count = await _service(session, membership, user).analyze_document(person_id, document_id)
    return AnalyzeDocumentResponse(
        document_id=document_id,
        suggestions_created=count,
        analysis_status="ready_for_review" if count else "complete",
    )


@router.get("/ai-suggestions", response_model=list[ProfileSuggestionResponse])
async def list_suggestions(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
    suggestion_status: str | None = Query(default=None, alias="status"),
) -> list[ProfileSuggestion]:
    return await _service(session, membership, user).list_suggestions(person_id, suggestion_status)


@router.patch("/ai-suggestions/{suggestion_id}", response_model=ProfileSuggestionResponse)
async def edit_suggestion(
    person_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    data: SuggestionEdit,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> ProfileSuggestion:
    _require(membership.role, REVIEW_ROLES)
    return await _service(session, membership, user).edit_suggestion(
        person_id, suggestion_id, data.model_dump(exclude_unset=True)
    )


@router.post("/ai-suggestions/{suggestion_id}/accept", response_model=ProfileSuggestionResponse)
async def accept_suggestion(
    person_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> ProfileSuggestion:
    _require(membership.role, REVIEW_ROLES)
    return await _service(session, membership, user).accept(person_id, suggestion_id)


@router.post("/ai-suggestions/{suggestion_id}/reject", response_model=ProfileSuggestionResponse)
async def reject_suggestion(
    person_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> ProfileSuggestion:
    _require(membership.role, REVIEW_ROLES)
    return await _service(session, membership, user).reject(person_id, suggestion_id)


@router.get("/completeness", response_model=ProfileCompletenessResponse)
async def completeness(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> dict[str, object]:
    return await _service(session, membership, user).completeness(person_id)
