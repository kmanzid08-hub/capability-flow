import uuid

from fastapi import APIRouter, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.dependencies import ActiveMembership, SessionDep
from app.models.enums import MembershipRole
from app.models.membership import OrganizationMembership
from app.models.user import User
from app.schemas.member import MemberCreate, MemberResponse, MemberUpdate

router = APIRouter(
    prefix="/organizations/members",
    tags=["organization-members"],
)

ADMIN_ROLES = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
}

PASSWORD_HASH = PasswordHash.recommended()


def require_admin(membership: OrganizationMembership) -> None:
    if membership.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner or admin access is required",
        )


async def load_members(
    session: SessionDep,
    organization_id: uuid.UUID,
) -> list[OrganizationMembership]:
    result = await session.scalars(
        select(OrganizationMembership)
        .options(joinedload(OrganizationMembership.user))
        .where(
            OrganizationMembership.organization_id == organization_id,
        )
        .order_by(OrganizationMembership.created_at.asc())
    )
    return list(result.unique())


def response_for(
    membership: OrganizationMembership,
) -> MemberResponse:
    return MemberResponse(
        id=membership.id,
        user_id=membership.user_id,
        email=membership.user.email,
        full_name=membership.user.full_name,
        role=membership.role,
        is_active=membership.is_active,
        created_at=membership.created_at,
    )


@router.get("", response_model=list[MemberResponse])
async def list_members(
    membership: ActiveMembership,
    session: SessionDep,
) -> list[MemberResponse]:
    require_admin(membership)

    members = await load_members(
        session,
        membership.organization_id,
    )
    return [response_for(item) for item in members]


@router.post(
    "",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_member(
    data: MemberCreate,
    membership: ActiveMembership,
    session: SessionDep,
) -> MemberResponse:
    require_admin(membership)

    email = str(data.email).strip().lower()

    existing_user = await session.scalar(
        select(User).where(
            func.lower(User.email) == email,
        )
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A user with this email already exists. "
                "Use a different email or contact the workspace owner."
            ),
        )

    user = User(
        email=email,
        full_name=data.full_name.strip(),
        password_hash=PASSWORD_HASH.hash(data.password),
        is_active=True,
    )
    session.add(user)
    await session.flush()

    new_membership = OrganizationMembership(
        organization_id=membership.organization_id,
        user_id=user.id,
        role=data.role,
        is_active=True,
    )
    session.add(new_membership)

    await session.commit()

    created = await session.scalar(
        select(OrganizationMembership)
        .options(joinedload(OrganizationMembership.user))
        .where(
            OrganizationMembership.id == new_membership.id,
            OrganizationMembership.organization_id == membership.organization_id,
        )
    )
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Member was created but could not be reloaded",
        )

    return response_for(created)


@router.patch(
    "/{membership_id}",
    response_model=MemberResponse,
)
async def update_member(
    membership_id: uuid.UUID,
    data: MemberUpdate,
    membership: ActiveMembership,
    session: SessionDep,
) -> MemberResponse:
    require_admin(membership)

    target = await session.scalar(
        select(OrganizationMembership)
        .options(joinedload(OrganizationMembership.user))
        .where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == membership.organization_id,
        )
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization member not found",
        )

    removing_owner = target.role == MembershipRole.OWNER and (
        data.role is not None and data.role != MembershipRole.OWNER or data.is_active is False
    )

    if removing_owner:
        active_owner_count = await session.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(
                OrganizationMembership.organization_id == membership.organization_id,
                OrganizationMembership.role == MembershipRole.OWNER,
                OrganizationMembership.is_active.is_(True),
            )
        )

        if int(active_owner_count or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The workspace must keep at least one active owner",
            )

    if data.role is not None:
        target.role = data.role

    if data.is_active is not None:
        target.is_active = data.is_active

    await session.commit()
    await session.refresh(target)
    return response_for(target)
