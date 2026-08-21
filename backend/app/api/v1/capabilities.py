import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import ActiveMembership, SessionDep
from app.models.capability import (
    PersonCertification,
    PersonEducation,
    PersonSkill,
)
from app.models.enums import MembershipRole
from app.schemas.capability import (
    CertificationCreate,
    CertificationResponse,
    CertificationUpdate,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)
from app.services.capabilities import CapabilityService

router = APIRouter(
    prefix="/people/{person_id}",
    tags=["capabilities"],
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
    "/skills",
    response_model=list[SkillResponse],
)
async def list_skills(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> list[PersonSkill]:
    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.list_skills(person_id)


@router.post(
    "/skills",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_skill(
    person_id: uuid.UUID,
    data: SkillCreate,
    membership: ActiveMembership,
    session: SessionDep,
) -> PersonSkill:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.create_skill(
        person_id,
        data,
    )


@router.patch(
    "/skills/{skill_id}",
    response_model=SkillResponse,
)
async def update_skill(
    person_id: uuid.UUID,
    skill_id: uuid.UUID,
    data: SkillUpdate,
    membership: ActiveMembership,
    session: SessionDep,
) -> PersonSkill:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.update_skill(
        person_id,
        skill_id,
        data,
    )


@router.delete(
    "/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_skill(
    person_id: uuid.UUID,
    skill_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> Response:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    await service.delete_skill(
        person_id,
        skill_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get(
    "/education",
    response_model=list[EducationResponse],
)
async def list_education(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> list[PersonEducation]:
    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.list_education(person_id)


@router.post(
    "/education",
    response_model=EducationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_education(
    person_id: uuid.UUID,
    data: EducationCreate,
    membership: ActiveMembership,
    session: SessionDep,
) -> PersonEducation:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.create_education(
        person_id,
        data,
    )


@router.patch(
    "/education/{education_id}",
    response_model=EducationResponse,
)
async def update_education(
    person_id: uuid.UUID,
    education_id: uuid.UUID,
    data: EducationUpdate,
    membership: ActiveMembership,
    session: SessionDep,
) -> PersonEducation:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.update_education(
        person_id,
        education_id,
        data,
    )


@router.delete(
    "/education/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_education(
    person_id: uuid.UUID,
    education_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> Response:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    await service.delete_education(
        person_id,
        education_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get(
    "/certifications",
    response_model=list[CertificationResponse],
)
async def list_certifications(
    person_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> list[PersonCertification]:
    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.list_certifications(person_id)


@router.post(
    "/certifications",
    response_model=CertificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_certification(
    person_id: uuid.UUID,
    data: CertificationCreate,
    membership: ActiveMembership,
    session: SessionDep,
) -> PersonCertification:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.create_certification(
        person_id,
        data,
    )


@router.patch(
    "/certifications/{certification_id}",
    response_model=CertificationResponse,
)
async def update_certification(
    person_id: uuid.UUID,
    certification_id: uuid.UUID,
    data: CertificationUpdate,
    membership: ActiveMembership,
    session: SessionDep,
) -> PersonCertification:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    return await service.update_certification(
        person_id,
        certification_id,
        data,
    )


@router.delete(
    "/certifications/{certification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_certification(
    person_id: uuid.UUID,
    certification_id: uuid.UUID,
    membership: ActiveMembership,
    session: SessionDep,
) -> Response:
    require_write_access(membership)

    service = CapabilityService(
        session,
        membership.organization_id,
    )

    await service.delete_certification(
        person_id,
        certification_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
