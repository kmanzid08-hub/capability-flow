from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


def stored_files(
    root: Path,
) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


async def register(
    client: AsyncClient,
    suffix: str,
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": (f"Documents {suffix}"),
            "organization_slug": (f"documents-{suffix}"),
            "full_name": (f"Owner {suffix}"),
            "email": (f"documents-{suffix}@example.com"),
            "password": ("correct-horse-battery-staple"),
        },
    )

    assert response.status_code == 201

    return response.json()


def headers(
    registration: dict[str, str],
) -> dict[str, str]:
    return {
        "Authorization": (f"Bearer {registration['access_token']}"),
        "X-Organization-ID": (registration["organization_id"]),
    }


async def create_person(
    client: AsyncClient,
    registration: dict[str, str],
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/people",
        headers=headers(
            registration,
        ),
        json={
            "first_name": "Amina",
            "last_name": "Kamanzi",
            "professional_title": ("Senior Engineer"),
        },
    )

    assert response.status_code == 201

    return response.json()


@pytest.fixture
def document_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    storage = tmp_path / "uploads"

    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "document_storage_path",
        storage,
    )

    monkeypatch.setattr(
        settings,
        "document_max_file_size_mb",
        25,
    )

    return storage


async def test_document_upload_download_and_delete(
    client: AsyncClient,
    document_storage: Path,
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

    contents = b"This is a test CV document."

    uploaded = await client.post(
        f"/api/v1/people/{person_id}/documents",
        headers=headers(
            registration,
        ),
        data={
            "document_type": "cv",
            "title": "Amina CV",
            "description": ("Current professional CV"),
        },
        files={
            "file": (
                "amina-cv.docx",
                contents,
                ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ),
        },
    )

    assert uploaded.status_code == 201, uploaded.text

    document = uploaded.json()

    assert document["title"] == "Amina CV"
    assert document["document_type"] == "cv"

    assert document["original_filename"] == "amina-cv.docx"

    assert document["file_extension"] == ".docx"

    assert document["file_size"] == len(
        contents,
    )

    files = stored_files(
        document_storage,
    )

    assert len(files) == 1

    listed = await client.get(
        f"/api/v1/people/{person_id}/documents",
        headers=headers(
            registration,
        ),
    )

    assert listed.status_code == 200
    assert len(listed.json()) == 1

    document_id = document["id"]

    downloaded = await client.get(
        (f"/api/v1/people/{person_id}/documents/{document_id}/download"),
        headers=headers(
            registration,
        ),
    )

    assert downloaded.status_code == 200
    assert downloaded.content == contents

    deleted = await client.delete(
        (f"/api/v1/people/{person_id}/documents/{document_id}"),
        headers=headers(
            registration,
        ),
    )

    assert deleted.status_code == 204

    listed_after_delete = await client.get(
        f"/api/v1/people/{person_id}/documents",
        headers=headers(
            registration,
        ),
    )

    assert listed_after_delete.status_code == 200

    assert listed_after_delete.json() == []

    assert not stored_files(
        document_storage,
    )


async def test_document_access_is_tenant_isolated(
    client: AsyncClient,
    document_storage: Path,
) -> None:
    first = await register(
        client,
        "first",
    )

    second = await register(
        client,
        "second",
    )

    person = await create_person(
        client,
        first,
    )

    person_id = person["id"]

    uploaded = await client.post(
        f"/api/v1/people/{person_id}/documents",
        headers=headers(
            first,
        ),
        data={
            "document_type": "certificate",
            "title": "Certificate",
        },
        files={
            "file": (
                "certificate.pdf",
                b"certificate-data",
                "application/pdf",
            ),
        },
    )

    assert uploaded.status_code == 201

    document_id = uploaded.json()["id"]

    foreign_list = await client.get(
        f"/api/v1/people/{person_id}/documents",
        headers=headers(
            second,
        ),
    )

    assert foreign_list.status_code == 404

    foreign_download = await client.get(
        (f"/api/v1/people/{person_id}/documents/{document_id}/download"),
        headers=headers(
            second,
        ),
    )

    assert foreign_download.status_code == 404

    foreign_delete = await client.delete(
        (f"/api/v1/people/{person_id}/documents/{document_id}"),
        headers=headers(
            second,
        ),
    )

    assert foreign_delete.status_code == 404

    own_download = await client.get(
        (f"/api/v1/people/{person_id}/documents/{document_id}/download"),
        headers=headers(
            first,
        ),
    )

    assert own_download.status_code == 200

    assert (
        len(
            stored_files(
                document_storage,
            )
        )
        == 1
    )


async def test_unsafe_document_extension_is_rejected(
    client: AsyncClient,
    document_storage: Path,
) -> None:
    registration = await register(
        client,
        "unsafe",
    )

    person = await create_person(
        client,
        registration,
    )

    response = await client.post(
        (f"/api/v1/people/{person['id']}/documents"),
        headers=headers(
            registration,
        ),
        data={
            "document_type": "other",
        },
        files={
            "file": (
                "dangerous.exe",
                b"not really executable",
                "application/octet-stream",
            ),
        },
    )

    assert response.status_code == 415

    assert not stored_files(
        document_storage,
    )


async def test_document_size_limit_is_enforced(
    client: AsyncClient,
    document_storage: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "document_max_file_size_mb",
        1,
    )

    registration = await register(
        client,
        "large",
    )

    person = await create_person(
        client,
        registration,
    )

    contents = b"x" * (1024 * 1024 + 1)

    response = await client.post(
        (f"/api/v1/people/{person['id']}/documents"),
        headers=headers(
            registration,
        ),
        data={
            "document_type": "report",
        },
        files={
            "file": (
                "large.pdf",
                contents,
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 413

    assert not stored_files(
        document_storage,
    )
