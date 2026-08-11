import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, OrganizationMembership, User
from app.models.enums import MembershipRole


async def register(client: AsyncClient, suffix: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Example {suffix}",
            "organization_slug": f"example-{suffix}",
            "full_name": f"Owner {suffix}",
            "email": f"owner-{suffix}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def headers(registration: dict[str, str]) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {registration['access_token']}",
        "X-Organization-ID": registration["organization_id"],
    }


async def test_registration_creates_organization_user_and_owner(
    client: AsyncClient, session: AsyncSession
) -> None:
    data = await register(client, "registration")
    assert await session.get(Organization, uuid.UUID(data["organization_id"]))
    assert await session.get(User, uuid.UUID(data["user_id"]))
    membership = await session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == uuid.UUID(data["organization_id"]),
            OrganizationMembership.user_id == uuid.UUID(data["user_id"]),
        )
    )
    assert membership is not None and membership.role == MembershipRole.OWNER


async def test_login_and_me(client: AsyncClient) -> None:
    await register(client, "login")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner-login@example.com", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "owner-login@example.com"


async def test_person_crud_is_tenant_isolated(client: AsyncClient) -> None:
    first = await register(client, "first")
    second = await register(client, "second")
    created = await client.post(
        "/api/v1/people",
        headers=headers(first),
        json={"first_name": "Amina", "last_name": "Kamanzi", "professional_title": "Engineer"},
    )
    assert created.status_code == 201
    person_id = created.json()["id"]
    own_get = await client.get(f"/api/v1/people/{person_id}", headers=headers(first))
    assert own_get.status_code == 200
    assert own_get.json()["display_name"] == "Amina Kamanzi"
    assert (
        await client.get(f"/api/v1/people/{person_id}", headers=headers(second))
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/people/{person_id}", headers=headers(second), json={"first_name": "Changed"}
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/people/{person_id}", headers=headers(second))
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/people/{person_id}", headers=headers(first))
    ).status_code == 200
    assert (
        await client.delete(f"/api/v1/people/{person_id}", headers=headers(first))
    ).status_code == 204
    assert (
        await client.get(f"/api/v1/people/{person_id}", headers=headers(first))
    ).status_code == 404


async def test_duplicate_membership_is_rejected(client: AsyncClient, session: AsyncSession) -> None:
    data = await register(client, "duplicate")
    session.add(
        OrganizationMembership(
            organization_id=uuid.UUID(data["organization_id"]),
            user_id=uuid.UUID(data["user_id"]),
            role=MembershipRole.VIEWER,
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_unauthenticated_requests_are_rejected(client: AsyncClient) -> None:
    for method, path in [("GET", "/api/v1/auth/me"), ("GET", "/api/v1/people")]:
        assert (await client.request(method, path)).status_code == 401
