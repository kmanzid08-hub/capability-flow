from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.api.dependencies import CurrentUser, SessionDep
from app.models.enums import MembershipRole
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    MembershipSummary,
    RegisterOrganizationRequest,
    RegistrationResponse,
    TokenResponse,
)
from app.security.jwt import create_access_token
from app.security.passwords import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register-organization",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_organization(
    data: RegisterOrganizationRequest, session: SessionDep
) -> RegistrationResponse:
    organization = Organization(name=data.organization_name.strip(), slug=data.organization_slug)
    user = User(
        email=str(data.email).lower(),
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
    )
    try:
        async with session.begin():
            session.add_all([organization, user])
            await session.flush()
            session.add(
                OrganizationMembership(
                    organization_id=organization.id,
                    user_id=user.id,
                    role=MembershipRole.OWNER,
                )
            )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug or user email is already registered",
        ) from None
    return RegistrationResponse(
        organization_id=organization.id,
        user_id=user.id,
        access_token=create_access_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: SessionDep) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == str(data.email).lower()))
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: CurrentUser, session: SessionDep) -> CurrentUserResponse:
    memberships = list(
        (
            await session.scalars(
                select(OrganizationMembership)
                .options(joinedload(OrganizationMembership.organization))
                .where(
                    OrganizationMembership.user_id == user.id,
                    OrganizationMembership.is_active.is_(True),
                )
            )
        ).unique()
    )
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        memberships=[
            MembershipSummary(
                organization_id=item.organization_id,
                organization_name=item.organization.name,
                organization_slug=item.organization.slug,
                role=item.role,
            )
            for item in memberships
        ],
    )
