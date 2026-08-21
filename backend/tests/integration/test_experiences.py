from httpx import AsyncClient


async def register(
    client: AsyncClient,
    suffix: str,
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Experience {suffix}",
            "organization_slug": f"experience-{suffix}",
            "full_name": f"Owner {suffix}",
            "email": f"experience-{suffix}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 201

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
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/people",
        headers=headers(registration),
        json={
            "first_name": "Amina",
            "last_name": "Kamanzi",
            "professional_title": "Senior Specialist",
        },
    )

    assert response.status_code == 201

    return response.json()


async def test_employment_and_project_crud(
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

    employment = await client.post(
        f"/api/v1/people/{person_id}/employment",
        headers=headers(registration),
        json={
            "employer_name": "Example Group",
            "job_title": "Senior Engineer",
            "employment_type": "full_time",
            "industry": "Technology",
            "country": "Rwanda",
            "start_date": "2020-01-01",
            "end_date": "2024-06-30",
            "responsibilities": "Led platform delivery.",
            "achievements": "Delivered major systems.",
        },
    )

    assert employment.status_code == 201, employment.text

    employment_id = employment.json()["id"]

    employment_update = await client.patch(
        (f"/api/v1/people/{person_id}/employment/{employment_id}"),
        headers=headers(registration),
        json={
            "job_title": "Principal Engineer",
        },
    )

    assert employment_update.status_code == 200
    assert employment_update.json()["job_title"] == "Principal Engineer"

    project = await client.post(
        f"/api/v1/people/{person_id}/projects",
        headers=headers(registration),
        json={
            "project_name": "National Data Platform",
            "client_name": "Example Client",
            "role": "Technical Lead",
            "sector": "Public Sector",
            "country": "Rwanda",
            "start_date": "2022-02-01",
            "end_date": "2023-08-31",
            "description": "Large data platform implementation.",
            "skills_summary": "Python, PostgreSQL, cloud architecture",
        },
    )

    assert project.status_code == 201, project.text

    project_id = project.json()["id"]

    employment_list = await client.get(
        f"/api/v1/people/{person_id}/employment",
        headers=headers(registration),
    )

    assert employment_list.status_code == 200
    assert len(employment_list.json()) == 1

    project_list = await client.get(
        f"/api/v1/people/{person_id}/projects",
        headers=headers(registration),
    )

    assert project_list.status_code == 200
    assert len(project_list.json()) == 1

    project_delete = await client.delete(
        (f"/api/v1/people/{person_id}/projects/{project_id}"),
        headers=headers(registration),
    )

    assert project_delete.status_code == 204


async def test_experiences_are_tenant_isolated(
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
    )

    person_id = person["id"]

    employment = await client.post(
        f"/api/v1/people/{person_id}/employment",
        headers=headers(first),
        json={
            "employer_name": "Private Employer",
            "job_title": "Director",
            "start_date": "2021-01-01",
            "is_current": True,
        },
    )

    assert employment.status_code == 201

    experience_id = employment.json()["id"]

    foreign_list = await client.get(
        f"/api/v1/people/{person_id}/employment",
        headers=headers(second),
    )

    assert foreign_list.status_code == 404

    foreign_update = await client.patch(
        (f"/api/v1/people/{person_id}/employment/{experience_id}"),
        headers=headers(second),
        json={
            "job_title": "Changed",
        },
    )

    assert foreign_update.status_code == 404

    own_list = await client.get(
        f"/api/v1/people/{person_id}/employment",
        headers=headers(first),
    )

    assert own_list.status_code == 200
    assert own_list.json()[0]["job_title"] == "Director"


async def test_experience_date_validation(
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

    invalid_employment = await client.post(
        f"/api/v1/people/{person_id}/employment",
        headers=headers(registration),
        json={
            "employer_name": "Example",
            "job_title": "Engineer",
            "start_date": "2024-01-01",
            "end_date": "2023-01-01",
        },
    )

    assert invalid_employment.status_code == 422

    invalid_project = await client.post(
        f"/api/v1/people/{person_id}/projects",
        headers=headers(registration),
        json={
            "project_name": "Current Project",
            "role": "Lead",
            "start_date": "2025-01-01",
            "end_date": "2026-01-01",
            "is_current": True,
        },
    )

    assert invalid_project.status_code == 422
