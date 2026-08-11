import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import MembershipRole
from app.schemas.common import AuditFields, ORMModel


class RegisterOrganizationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    organization_slug: str = Field(
        min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MembershipSummary(ORMModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    role: MembershipRole


class UserResponse(AuditFields):
    email: EmailStr
    full_name: str
    is_active: bool


class CurrentUserResponse(UserResponse):
    memberships: list[MembershipSummary]


class RegistrationResponse(BaseModel):
    organization_id: uuid.UUID
    user_id: uuid.UUID
    access_token: str
    token_type: str = "bearer"
