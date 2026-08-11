import uuid

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.dependencies import ActiveMembership, CurrentUser, SessionDep
from app.models.enums import MembershipRole
from app.models.person import Person
from app.repositories.people import PersonRepository
from app.schemas.person import PeoplePage, PersonCreate, PersonResponse, PersonUpdate
from app.services.people import PersonService

router = APIRouter(prefix="/people", tags=["people"])
WRITE_ROLES = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
    MembershipRole.MANAGER,
    MembershipRole.DATA_ENTRY,
}


def require_write_access(membership: ActiveMembership) -> None:
    if membership.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Write access is required"
        )


@router.get("", response_model=PeoplePage)
async def list_people(
    membership: ActiveMembership,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PeoplePage:
    items, total = await PersonRepository(session, membership.organization_id).list(
        limit=limit, offset=offset
    )
    return PeoplePage(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
    data: PersonCreate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Person:
    require_write_access(membership)
    return await PersonService(session, membership.organization_id, user.id).create(data)


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Person:
    return await PersonService(session, membership.organization_id, user.id).get_or_404(person_id)


@router.patch("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: uuid.UUID,
    data: PersonUpdate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Person:
    require_write_access(membership)
    return await PersonService(session, membership.organization_id, user.id).update(person_id, data)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_person(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Response:
    require_write_access(membership)
    await PersonService(session, membership.organization_id, user.id).archive(person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
