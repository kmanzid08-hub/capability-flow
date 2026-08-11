import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.models.enums import OrganizationStatus
from app.models.membership import OrganizationMembership
from app.models.user import User
from app.security.jwt import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)
SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized from None
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_active_membership(
    session: SessionDep,
    user: CurrentUser,
    organization_id: Annotated[uuid.UUID | None, Header(alias="X-Organization-ID")] = None,
) -> OrganizationMembership:
    query = (
        select(OrganizationMembership)
        .options(joinedload(OrganizationMembership.organization))
        .where(
            OrganizationMembership.user_id == user.id, OrganizationMembership.is_active.is_(True)
        )
    )
    if organization_id is not None:
        query = query.where(OrganizationMembership.organization_id == organization_id)
    memberships = list((await session.scalars(query)).unique())
    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No active membership for organization"
        )
    if organization_id is None and len(memberships) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Organization-ID is required when the user belongs to multiple organizations",
        )
    membership = memberships[0]
    if membership.organization.status != OrganizationStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Organization is not active"
        )
    return membership


ActiveMembership = Annotated[OrganizationMembership, Depends(get_active_membership)]
