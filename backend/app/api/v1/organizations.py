from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import ActiveMembership, CurrentUser, SessionDep
from app.models.enums import MembershipRole
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.schemas.organization import CurrentOrganizationResponse

router = APIRouter(prefix="/organizations", tags=["organizations"])


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


@router.post(
    "",
    response_model=CurrentOrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    data: WorkspaceCreate,
    user: CurrentUser,
    session: SessionDep,
) -> CurrentOrganizationResponse:
    organization = Organization(
        name=data.name.strip(),
        slug=data.slug.strip().lower(),
    )
    membership = OrganizationMembership(
        organization=organization,
        user_id=user.id,
        role=MembershipRole.OWNER,
        is_active=True,
    )

    try:
        session.add_all([organization, membership])
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That workspace slug is already in use",
        ) from None

    await session.refresh(organization)
    await session.refresh(membership)

    return CurrentOrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        status=organization.status,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        membership_id=membership.id,
        role=membership.role,
    )


@router.get("/current", response_model=CurrentOrganizationResponse)
async def current_organization(
    membership: ActiveMembership,
) -> CurrentOrganizationResponse:
    organization = membership.organization
    return CurrentOrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        status=organization.status,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        membership_id=membership.id,
        role=membership.role,
    )
