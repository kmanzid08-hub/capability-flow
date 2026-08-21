from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.schemas.opportunity import ExtractedOpportunity


async def register(client: AsyncClient, suffix: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Opportunity {suffix}",
            "organization_slug": f"opportunity-{suffix}",
            "full_name": f"Owner {suffix}",
            "email": f"opportunity-{suffix}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201
    return response.json()


def headers(registration: dict[str, str]) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {registration['access_token']}",
        "X-Organization-ID": registration["organization_id"],
    }


async def create_person_with_capabilities(client: AsyncClient, registration: dict[str, str]) -> str:
    person = await client.post(
        "/api/v1/people",
        headers=headers(registration),
        json={
            "first_name": "Amina",
            "last_name": "Kamanzi",
            "professional_title": "Senior Data Engineer",
            "availability_status": "available",
            "profile_status": "active",
        },
    )
    assert person.status_code == 201
    person_id = person.json()["id"]
    assert (
        await client.post(
            f"/api/v1/people/{person_id}/skills",
            headers=headers(registration),
            json={"name": "Python", "proficiency": "expert", "years_experience": 8},
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/api/v1/people/{person_id}/skills",
            headers=headers(registration),
            json={"name": "PostgreSQL", "proficiency": "advanced", "years_experience": 7},
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/api/v1/people/{person_id}/education",
            headers=headers(registration),
            json={
                "degree_level": "master",
                "degree_name": "MSc Computer Science",
                "field_of_study": "Computer Science",
                "institution": "Example University",
            },
        )
    ).status_code == 201
    return person_id


async def test_opportunity_is_tenant_scoped(client: AsyncClient) -> None:
    first = await register(client, "first")
    second = await register(client, "second")
    created = await client.post(
        "/api/v1/opportunities",
        headers=headers(first),
        json={"title": "Digital platform tender"},
    )
    assert created.status_code == 201
    opportunity_id = created.json()["id"]
    assert (
        await client.get(
            f"/api/v1/opportunities/{opportunity_id}",
            headers=headers(first),
        )
    ).status_code == 200
    assert (
        await client.get(
            f"/api/v1/opportunities/{opportunity_id}",
            headers=headers(second),
        )
    ).status_code == 404


async def test_ai_extraction_matching_and_team_generation(client: AsyncClient) -> None:
    registration = await register(client, "analysis")
    person_id = await create_person_with_capabilities(client, registration)
    opportunity = await client.post(
        "/api/v1/opportunities",
        headers=headers(registration),
        json={"title": "Data engineering assignment"},
    )
    assert opportunity.status_code == 201
    opportunity_id = opportunity.json()["id"]
    source = await client.post(
        f"/api/v1/opportunities/{opportunity_id}/sources/text",
        headers=headers(registration),
        json={
            "text": (
                "We need one Senior Data Engineer with Python, PostgreSQL and "
                "a Master's degree in Computer Science."
            )
        },
    )
    assert source.status_code == 201
    extracted = ExtractedOpportunity.model_validate(
        {
            "summary": "Senior Data Engineer required.",
            "roles": [
                {
                    "title": "Senior Data Engineer",
                    "quantity": 1,
                    "requirements": [
                        {
                            "requirement_type": "skill",
                            "importance": "mandatory",
                            "label": "Python",
                            "normalized_value": "Python",
                            "minimum_years": 5,
                            "weight": 3,
                        },
                        {
                            "requirement_type": "skill",
                            "importance": "mandatory",
                            "label": "PostgreSQL",
                            "normalized_value": "PostgreSQL",
                            "weight": 3,
                        },
                        {
                            "requirement_type": "education",
                            "importance": "mandatory",
                            "label": "Master's in Computer Science",
                            "normalized_value": "Computer Science",
                            "minimum_degree_level": "master",
                            "weight": 3,
                        },
                    ],
                }
            ],
        }
    )
    with patch(
        "app.services.opportunities.ClaudeRequirementExtractor.extract",
        new=AsyncMock(return_value=extracted),
    ):
        analyzed = await client.post(
            f"/api/v1/opportunities/{opportunity_id}/analyze",
            headers=headers(registration),
        )
    assert analyzed.status_code == 200, analyzed.text
    assert analyzed.json()["status"] == "complete"
    roles = await client.get(
        f"/api/v1/opportunities/{opportunity_id}/roles",
        headers=headers(registration),
    )
    assert roles.status_code == 200
    role_id = roles.json()[0]["id"]
    matches = await client.get(
        f"/api/v1/opportunities/{opportunity_id}/roles/{role_id}/matches",
        headers=headers(registration),
    )
    assert matches.status_code == 200
    assert matches.json()[0]["person_id"] == person_id
    assert matches.json()[0]["score"] >= 95
    assert matches.json()[0]["mandatory_failed"] is False
    teams = await client.get(
        f"/api/v1/opportunities/{opportunity_id}/teams",
        headers=headers(registration),
    )
    assert teams.status_code == 200
    assert teams.json()[0]["members"][0]["person_id"] == person_id

    team_id = teams.json()[0]["id"]
    selected = await client.post(
        f"/api/v1/opportunities/{opportunity_id}/teams/{team_id}/select",
        headers=headers(registration),
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["selected_team_id"] == team_id
    assert selected.json()["selected_team_at"] is not None

    pursuing = await client.patch(
        f"/api/v1/opportunities/{opportunity_id}",
        headers=headers(registration),
        json={"status": "pursuing", "internal_notes": "Bid team approved."},
    )
    assert pursuing.status_code == 200, pursuing.text
    assert pursuing.json()["status"] == "pursuing"
    assert pursuing.json()["decision_at"] is not None
    assert pursuing.json()["internal_notes"] == "Bid team approved."

    submitted = await client.patch(
        f"/api/v1/opportunities/{opportunity_id}",
        headers=headers(registration),
        json={"status": "submitted"},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submitted_at"] is not None

    won = await client.patch(
        f"/api/v1/opportunities/{opportunity_id}",
        headers=headers(registration),
        json={"status": "won", "outcome_notes": "Client issued award notice."},
    )
    assert won.status_code == 200, won.text
    assert won.json()["status"] == "won"
    assert won.json()["outcome_at"] is not None
    assert won.json()["outcome_notes"] == "Client issued award notice."


async def test_submission_requires_selected_team(client: AsyncClient) -> None:
    registration = await register(client, "submission-guard")
    created = await client.post(
        "/api/v1/opportunities",
        headers=headers(registration),
        json={"title": "Guarded submission"},
    )
    assert created.status_code == 201
    opportunity_id = created.json()["id"]

    ready = await client.patch(
        f"/api/v1/opportunities/{opportunity_id}",
        headers=headers(registration),
        json={"status": "ready"},
    )
    assert ready.status_code == 200

    pursuing = await client.patch(
        f"/api/v1/opportunities/{opportunity_id}",
        headers=headers(registration),
        json={"status": "pursuing"},
    )
    assert pursuing.status_code == 200

    submitted = await client.patch(
        f"/api/v1/opportunities/{opportunity_id}",
        headers=headers(registration),
        json={"status": "submitted"},
    )
    assert submitted.status_code == 409


async def test_text_intake_creates_opportunity_and_preserves_source(client: AsyncClient) -> None:
    registration = await register(client, "intake-text")
    response = await client.post(
        "/api/v1/opportunities/intake/text",
        headers=headers(registration),
        json={
            "text": (
                "Digital Health Platform Implementation\n"
                "Reference No: RFP-2026-0042\n"
                "Submission deadline: 2026-10-14\n"
                "The supplier shall provide a senior implementation team."
            )
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    opportunity = body["opportunity"]
    source = body["source"]
    assert opportunity["title"] == "Digital Health Platform Implementation"
    assert opportunity["reference_number"] == "RFP-2026-0042"
    assert opportunity["deadline_at"].startswith("2026-10-14")
    assert source["source_type"] == "pasted_text"

    listed = await client.get(
        f"/api/v1/opportunities/{opportunity['id']}/sources",
        headers=headers(registration),
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == source["id"]


async def test_file_intake_stores_downloadable_snapshot(client: AsyncClient) -> None:
    registration = await register(client, "intake-file")
    content = (
        b"Cybersecurity Advisory Services\n"
        b"Reference: TENDER-2026-9001\n"
        b"Deadline: 2026-11-20\n"
        b"The bidder must provide qualified security specialists."
    )
    response = await client.post(
        "/api/v1/opportunities/intake/file",
        headers=headers(registration),
        files={"file": ("requirements.txt", content, "text/plain")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    source = body["source"]
    opportunity_id = body["opportunity"]["id"]
    assert source["file_size"] == len(content)

    download = await client.get(
        f"/api/v1/opportunities/{opportunity_id}/sources/{source['id']}/download",
        headers=headers(registration),
    )
    assert download.status_code == 200
    assert download.content == content

    removed = await client.delete(
        f"/api/v1/opportunities/{opportunity_id}/sources/{source['id']}",
        headers=headers(registration),
    )
    assert removed.status_code == 204
