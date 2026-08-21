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
from fastapi.responses import FileResponse

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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access is required",
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
    service = DocumentService(
        session,
        membership.organization_id,
        user.id,
    )

    return await service.list_documents(
        person_id,
    )


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
    file: Annotated[
        UploadFile,
        File(),
    ],
    document_type: Annotated[
        DocumentType,
        Form(),
    ],
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
    require_write_access(
        membership,
    )

    service = DocumentService(
        session,
        membership.organization_id,
        user.id,
    )

    return await service.upload_document(
        person_id=person_id,
        upload=file,
        document_type=document_type,
        title=title,
        description=description,
        certification_id=certification_id,
        education_id=education_id,
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
    require_write_access(
        membership,
    )

    service = DocumentService(
        session,
        membership.organization_id,
        user.id,
    )

    return await service.update_document(
        person_id,
        document_id,
        data,
    )


@router.get(
    "/{document_id}/download",
    response_class=FileResponse,
)
async def download_document(
    person_id: uuid.UUID,
    document_id: uuid.UUID,
    membership: ActiveMembership,
    user: CurrentUser,
    session: SessionDep,
) -> FileResponse:
    service = DocumentService(
        session,
        membership.organization_id,
        user.id,
    )

    download = await service.get_download(
        person_id,
        document_id,
    )

    return FileResponse(
        path=download.path,
        media_type=(download.document.mime_type),
        filename=(download.document.original_filename),
        content_disposition_type="attachment",
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
    require_write_access(
        membership,
    )

    service = DocumentService(
        session,
        membership.organization_id,
        user.id,
    )

    await service.delete_document(
        person_id,
        document_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
