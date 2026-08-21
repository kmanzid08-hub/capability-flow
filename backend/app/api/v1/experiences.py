import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import ActiveMembership, SessionDep
from app.models.enums import MembershipRole
from app.models.experience import (
    EmploymentExperience,
    ProjectExperience,
)
from app.schemas.experience import (
    EmploymentCreate,
    EmploymentResponse,
    EmploymentUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.experiences import ExperienceService

router = APIRouter(
    prefix="/people/{person_id}",
    tags=["experience"],
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
    "/employment",
    response_model=list[EmploymentResponse],
)
async def list_employment(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> list[EmploymentExperience]:
    service = ExperienceService(
        session,
        membership.organization_id,
    )

    return await service.list_employment(person_id)


@router.post(
    "/employment",
    response_model=EmploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_employment(
    person_id: uuid.UUID,
    data: EmploymentCreate,
    membership: ActiveMembership,
    session: SessionDep,
) -> EmploymentExperience:
    require_write_access(membership)

    service = ExperienceService(
        session,
        membership.organization_id,
    )

    return await service.create_employment(
        person_id,
        data,
    )


@router.patch(
    "/employment/{experience_id}",
    response_model=EmploymentResponse,
)
async def update_employment(
    person_id: uuid.UUID,
    experience_id: uuid.UUID,
    data: EmploymentUpdate,
    membership: ActiveMembership,
    session: SessionDep,
) -> EmploymentExperience:
    require_write_access(membership)

    service = ExperienceService(
        session,
        membership.organization_id,
    )

    return await service.update_employment(
        person_id,
        experience_id,
        data,
    )


@router.delete(
    "/employment/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_employment(
    person_id: uuid.UUID,
    experience_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> Response:
    require_write_access(membership)

    service = ExperienceService(
        session,
        membership.organization_id,
    )

    await service.delete_employment(
        person_id,
        experience_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get(
    "/projects",
    response_model=list[ProjectResponse],
)
async def list_projects(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> list[ProjectExperience]:
    service = ExperienceService(
        session,
        membership.organization_id,
    )

    return await service.list_projects(person_id)


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    person_id: uuid.UUID,
    data: ProjectCreate,
    membership: ActiveMembership,
    session: SessionDep,
) -> ProjectExperience:
    require_write_access(membership)

    service = ExperienceService(
        session,
        membership.organization_id,
    )

    return await service.create_project(
        person_id,
        data,
    )


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
)
async def update_project(
    person_id: uuid.UUID,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    membership: ActiveMembership,
    session: SessionDep,
) -> ProjectExperience:
    require_write_access(membership)

    service = ExperienceService(
        session,
        membership.organization_id,
    )

    return await service.update_project(
        person_id,
        project_id,
        data,
    )


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    person_id: uuid.UUID,
    project_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> Response:
    require_write_access(membership)

    service = ExperienceService(
        session,
        membership.organization_id,
    )

    await service.delete_project(
        person_id,
        project_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
