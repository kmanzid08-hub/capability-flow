import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.api.dependencies import (
    ActiveMembership,
    CurrentUser,
    SessionDep,
)
from app.models.document import PersonDocument
from app.models.enums import (
    DocumentType,
    MembershipRole,
)
from app.schemas.document import (
    DocumentMetadataUpdate,
    DocumentResponse,
)
from app.services.documents import DocumentService

router = APIRouter(
    prefix="/people/{person_id}/documents",
    tags=["documents"],
)

WRITE_ROLES = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
    MembershipRole.MANAGER,
    MembershipRole.DATA_ENTRY,
}


def require_write_access(
    membership: ActiveMembership,
) -> None:
    if membership.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=(status.HTTP_403_FORBIDDEN),
            detail="Write access is required",
        )


def service(
    session: SessionDep,
    membership: ActiveMembership,
    user: CurrentUser,
) -> DocumentService:
    return DocumentService(
        session,
        membership.organization_id,
        user.id,
    )


@router.get(
    "",
    response_model=list[DocumentResponse],
)
async def list_documents(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> list[PersonDocument]:
    return await service(
        session,
        membership,
        user,
    ).list_documents(person_id)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    document_type: Annotated[
        DocumentType,
        Form(),
    ] = DocumentType.OTHER,
    title: Annotated[
        str | None,
        Form(),
    ] = None,
    description: Annotated[
        str | None,
        Form(),
    ] = None,
    certification_id: Annotated[
        uuid.UUID | None,
        Form(),
    ] = None,
    education_id: Annotated[
        uuid.UUID | None,
        Form(),
    ] = None,
) -> PersonDocument:
    require_write_access(membership)

    return await service(
        session,
        membership,
        user,
    ).upload_document(
        person_id,
        file,
        document_type,
        title,
        description,
        certification_id,
        education_id,
    )


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
)
async def update_document(
    person_id: uuid.UUID,
    document_id: uuid.UUID,
    data: DocumentMetadataUpdate,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> PersonDocument:
    require_write_access(membership)

    return await service(
        session,
        membership,
        user,
    ).update_document(
        person_id,
        document_id,
        data,
    )


@router.get(
    "/{document_id}/download",
)
async def download_document(
    person_id: uuid.UUID,
    document_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Response:
    download = await service(
        session,
        membership,
        user,
    ).get_download(
        person_id,
        document_id,
    )

    filename = download.document.original_filename
    safe_filename = (
        filename.replace(
            '"',
            "",
        )
        .replace(
            "\r",
            "",
        )
        .replace(
            "\n",
            "",
        )
    )

    return Response(
        content=download.content,
        media_type=(download.document.mime_type or "application/octet-stream"),
        headers={"Content-Disposition": (f'attachment; filename="{safe_filename}"')},
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    person_id: uuid.UUID,
    document_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> Response:
    require_write_access(membership)

    await service(
        session,
        membership,
        user,
    ).delete_document(
        person_id,
        document_id,
    )

    return Response(status_code=(status.HTTP_204_NO_CONTENT))
