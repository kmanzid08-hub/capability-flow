import uuid

from httpx import AsyncClient


async def register(
    client: AsyncClient,
    suffix: str,
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Capability {suffix}",
            "organization_slug": f"capability-{suffix}",
            "full_name": f"Owner {suffix}",
            "email": f"capability-{suffix}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def headers(
    registration: dict[str, str],
) -> dict[str, str]:
    return {
        "Authorization": (f"Bearer {registration['access_token']}"),
        "X-Organization-ID": registration["organization_id"],
    }


async def create_person(
    client: AsyncClient,
    registration: dict[str, str],
    first_name: str = "Amina",
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/people",
        headers=headers(registration),
        json={
            "first_name": first_name,
            "last_name": "Kamanzi",
            "professional_title": "Senior Engineer",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


async def test_capability_crud(
    client: AsyncClient,
) -> None:
    registration = await register(
        client,
        "crud",
    )

    person = await create_person(
        client,
        registration,
    )

    person_id = person["id"]

    skill = await client.post(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(registration),
        json={
            "name": "Python",
            "proficiency": "expert",
            "years_experience": 8,
            "last_used_year": 2026,
        },
    )

    assert skill.status_code == 201, skill.text
    assert skill.json()["name"] == "Python"
    assert skill.json()["years_experience"] == 8

    skill_id = skill.json()["id"]

    skill_update = await client.patch(
        f"/api/v1/people/{person_id}/skills/{skill_id}",
        headers=headers(registration),
        json={
            "years_experience": 9,
        },
    )

    assert skill_update.status_code == 200
    assert skill_update.json()["years_experience"] == 9

    education = await client.post(
        f"/api/v1/people/{person_id}/education",
        headers=headers(registration),
        json={
            "degree_level": "master",
            "degree_name": "Master of Science",
            "field_of_study": "Computer Science",
            "institution": "Example University",
            "country": "Rwanda",
            "start_year": 2016,
            "graduation_year": 2018,
        },
    )

    assert education.status_code == 201, education.text
    assert education.json()["degree_level"] == "master"

    certification = await client.post(
        f"/api/v1/people/{person_id}/certifications",
        headers=headers(registration),
        json={
            "name": "Cloud Architecture",
            "issuer": "Example Institute",
            "credential_id": "CERT-001",
            "issue_date": "2024-01-10",
            "expiry_date": "2027-01-10",
            "verification_url": "https://example.com/cert/CERT-001",
        },
    )

    assert certification.status_code == 201, certification.text
    assert certification.json()["issuer"] == "Example Institute"

    skills = await client.get(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(registration),
    )

    assert skills.status_code == 200
    assert len(skills.json()) == 1

    education_list = await client.get(
        f"/api/v1/people/{person_id}/education",
        headers=headers(registration),
    )

    assert education_list.status_code == 200
    assert len(education_list.json()) == 1

    certifications = await client.get(
        f"/api/v1/people/{person_id}/certifications",
        headers=headers(registration),
    )

    assert certifications.status_code == 200
    assert len(certifications.json()) == 1

    deleted = await client.delete(
        f"/api/v1/people/{person_id}/skills/{skill_id}",
        headers=headers(registration),
    )

    assert deleted.status_code == 204

    skills_after_delete = await client.get(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(registration),
    )

    assert skills_after_delete.status_code == 200
    assert skills_after_delete.json() == []


async def test_capabilities_are_tenant_isolated(
    client: AsyncClient,
) -> None:
    first = await register(
        client,
        "tenant-first",
    )

    second = await register(
        client,
        "tenant-second",
    )

    person = await create_person(
        client,
        first,
        first_name="Jean",
    )

    person_id = person["id"]

    skill = await client.post(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(first),
        json={
            "name": "PostgreSQL",
            "proficiency": "advanced",
            "years_experience": 6,
        },
    )

    assert skill.status_code == 201

    skill_id = skill.json()["id"]

    foreign_list = await client.get(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(second),
    )

    assert foreign_list.status_code == 404

    foreign_update = await client.patch(
        f"/api/v1/people/{person_id}/skills/{skill_id}",
        headers=headers(second),
        json={
            "years_experience": 20,
        },
    )

    assert foreign_update.status_code == 404

    foreign_delete = await client.delete(
        f"/api/v1/people/{person_id}/skills/{skill_id}",
        headers=headers(second),
    )

    assert foreign_delete.status_code == 404

    original = await client.get(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(first),
    )

    assert original.status_code == 200
    assert len(original.json()) == 1
    assert original.json()[0]["years_experience"] == 6


async def test_capability_validation(
    client: AsyncClient,
) -> None:
    registration = await register(
        client,
        "validation",
    )

    person = await create_person(
        client,
        registration,
    )

    person_id = person["id"]

    invalid_skill = await client.post(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(registration),
        json={
            "name": "Python",
            "years_experience": -1,
        },
    )

    assert invalid_skill.status_code == 422

    invalid_education = await client.post(
        f"/api/v1/people/{person_id}/education",
        headers=headers(registration),
        json={
            "degree_level": "bachelor",
            "institution": "Example University",
            "start_year": 2020,
            "graduation_year": 2018,
        },
    )

    assert invalid_education.status_code == 422

    invalid_certification = await client.post(
        f"/api/v1/people/{person_id}/certifications",
        headers=headers(registration),
        json={
            "name": "Example Certification",
            "issue_date": "2026-01-01",
            "expiry_date": "2025-01-01",
        },
    )

    assert invalid_certification.status_code == 422


async def test_duplicate_skill_is_rejected(
    client: AsyncClient,
) -> None:
    registration = await register(
        client,
        "duplicate-skill",
    )

    person = await create_person(
        client,
        registration,
    )

    person_id = person["id"]

    payload = {
        "name": "Python",
        "proficiency": "advanced",
    }

    first = await client.post(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(registration),
        json=payload,
    )

    assert first.status_code == 201

    second = await client.post(
        f"/api/v1/people/{person_id}/skills",
        headers=headers(registration),
        json=payload,
    )

    assert second.status_code == 409


async def test_unknown_person_capabilities_return_404(
    client: AsyncClient,
) -> None:
    registration = await register(
        client,
        "unknown-person",
    )

    missing_person_id = uuid.uuid4()

    response = await client.get(
        f"/api/v1/people/{missing_person_id}/skills",
        headers=headers(registration),
    )

    assert response.status_code == 404
