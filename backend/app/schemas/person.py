import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import AvailabilityStatus, ProfileStatus
from app.schemas.common import AuditFields


class PersonFields(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=250)
    professional_title: str | None = Field(default=None, max_length=200)
    primary_email: EmailStr | None = None
    primary_phone: str | None = Field(default=None, max_length=50)
    nationality: str | None = Field(default=None, max_length=100)
    country_of_residence: str | None = Field(default=None, max_length=100)
    summary: str | None = None
    availability_status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    profile_status: ProfileStatus = ProfileStatus.DRAFT


class PersonCreate(PersonFields):
    pass


class PersonUpdate(BaseModel):
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )
    professional_title: str | None = Field(
        default=None,
        max_length=200,
    )
    primary_email: EmailStr | None = None
    primary_phone: str | None = Field(default=None, max_length=50)
    nationality: str | None = Field(default=None, max_length=100)
    country_of_residence: str | None = Field(
        default=None,
        max_length=100,
    )
    summary: str | None = None
    availability_status: AvailabilityStatus | None = None
    profile_status: ProfileStatus | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "PersonUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")

        return self


class PersonResponse(AuditFields, PersonFields):
    display_name: str
    organization_id: uuid.UUID
    created_by_user_id: uuid.UUID
    updated_by_user_id: uuid.UUID


class PeoplePage(BaseModel):
    items: list[PersonResponse]
    total: int
    limit: int
    offset: int
