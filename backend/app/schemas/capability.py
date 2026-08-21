import uuid
from datetime import date

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.models.enums import DegreeLevel, SkillProficiency
from app.schemas.common import AuditFields


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    proficiency: SkillProficiency | None = None
    years_experience: float | None = Field(default=None, ge=0, le=80)
    last_used_year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = None


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    proficiency: SkillProficiency | None = None
    years_experience: float | None = Field(default=None, ge=0, le=80)
    last_used_year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "SkillUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self


class SkillResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID
    name: str
    proficiency: SkillProficiency | None
    years_experience: float | None
    last_used_year: int | None
    notes: str | None


class EducationCreate(BaseModel):
    degree_level: DegreeLevel
    degree_name: str | None = Field(default=None, max_length=250)
    field_of_study: str | None = Field(default=None, max_length=200)
    institution: str = Field(min_length=1, max_length=250)
    country: str | None = Field(default=None, max_length=100)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    graduation_year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_years(self) -> "EducationCreate":
        if (
            self.start_year is not None
            and self.graduation_year is not None
            and self.graduation_year < self.start_year
        ):
            raise ValueError("Graduation year cannot be earlier than start year")
        return self


class EducationUpdate(BaseModel):
    degree_level: DegreeLevel | None = None
    degree_name: str | None = Field(default=None, max_length=250)
    field_of_study: str | None = Field(default=None, max_length=200)
    institution: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )
    country: str | None = Field(default=None, max_length=100)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    graduation_year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "EducationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self


class EducationResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID
    degree_level: DegreeLevel
    degree_name: str | None
    field_of_study: str | None
    institution: str
    country: str | None
    start_year: int | None
    graduation_year: int | None
    notes: str | None


class CertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    issuer: str | None = Field(default=None, max_length=250)
    credential_id: str | None = Field(default=None, max_length=200)
    issue_date: date | None = None
    expiry_date: date | None = None
    verification_url: HttpUrl | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "CertificationCreate":
        if (
            self.issue_date is not None
            and self.expiry_date is not None
            and self.expiry_date < self.issue_date
        ):
            raise ValueError("Expiry date cannot be earlier than issue date")
        return self


class CertificationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=250)
    issuer: str | None = Field(default=None, max_length=250)
    credential_id: str | None = Field(default=None, max_length=200)
    issue_date: date | None = None
    expiry_date: date | None = None
    verification_url: HttpUrl | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "CertificationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self


class CertificationResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID
    name: str
    issuer: str | None
    credential_id: str | None
    issue_date: date | None
    expiry_date: date | None
    verification_url: str | None
    notes: str | None
