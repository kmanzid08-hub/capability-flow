import uuid

from app.models.enums import MembershipRole, OrganizationStatus
from app.schemas.common import AuditFields


class CurrentOrganizationResponse(AuditFields):
    name: str
    slug: str
    status: OrganizationStatus
    membership_id: uuid.UUID
    role: MembershipRole
