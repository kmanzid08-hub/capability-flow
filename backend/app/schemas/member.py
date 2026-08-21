import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import MembershipRole


class MemberCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=12, max_length=200)
    role: MembershipRole = MembershipRole.DATA_ENTRY


class MemberUpdate(BaseModel):
    role: MembershipRole | None = None
    is_active: bool | None = None


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: MembershipRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
