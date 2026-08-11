from app.db.base import Base
from app.models import Organization, OrganizationMembership, Person, User


def test_models_configure_successfully() -> None:
    assert {Organization, User, OrganizationMembership, Person}
    assert {"organizations", "users", "organization_memberships", "people"} <= set(
        Base.metadata.tables
    )
