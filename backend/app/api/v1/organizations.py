from fastapi import APIRouter

from app.api.dependencies import ActiveMembership
from app.schemas.organization import CurrentOrganizationResponse

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/current", response_model=CurrentOrganizationResponse)
async def current_organization(membership: ActiveMembership) -> CurrentOrganizationResponse:
    organization = membership.organization
    return CurrentOrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        status=organization.status,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        membership_id=membership.id,
        role=membership.role,
    )
