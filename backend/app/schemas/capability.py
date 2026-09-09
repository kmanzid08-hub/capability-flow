import uuid

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.core.partial_dates import normalize_partial_date, validate_partial_date_range
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
    start_date: str | None = None
    graduation_date: str | None = None
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_year_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        values = dict(data)
        if "start_date" not in values and values.get("start_year") is not None:
            values["start_date"] = str(values["start_year"])
        if "graduation_date" not in values and values.get("graduation_year") is not None:
            values["graduation_date"] = str(values["graduation_year"])
        values.pop("start_year", None)
        values.pop("graduation_year", None)
        return values

    @field_validator("start_date", "graduation_date", mode="before")
    @classmethod
    def normalize_dates(cls, value: object) -> str | None:
        return normalize_partial_date(value)

    @model_validator(mode="after")
    def validate_dates(self) -> "EducationCreate":
        if self.start_date is not None:
            validate_partial_date_range(
                self.start_date,
                self.graduation_date,
                start_label="education start date",
                end_label="Graduation date",
            )
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
    start_date: str | None = None
    graduation_date: str | None = None
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_year_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        values = dict(data)
        if "start_date" not in values and values.get("start_year") is not None:
            values["start_date"] = str(values["start_year"])
        if "graduation_date" not in values and values.get("graduation_year") is not None:
            values["graduation_date"] = str(values["graduation_year"])
        values.pop("start_year", None)
        values.pop("graduation_year", None)
        return values

    @field_validator("start_date", "graduation_date", mode="before")
    @classmethod
    def normalize_dates(cls, value: object) -> str | None:
        return normalize_partial_date(value)

    @model_validator(mode="after")
    def validate_patch(self) -> "EducationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        if self.start_date is not None and self.graduation_date is not None:
            validate_partial_date_range(
                self.start_date,
                self.graduation_date,
                start_label="education start date",
                end_label="Graduation date",
            )
        return self


class EducationResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID
    degree_level: DegreeLevel
    degree_name: str | None
    field_of_study: str | None
    institution: str
    country: str | None
    start_date: str | None
    graduation_date: str | None
    notes: str | None


class CertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    issuer: str | None = Field(default=None, max_length=250)
    credential_id: str | None = Field(default=None, max_length=200)
    issue_date: str | None = None
    expiry_date: str | None = None
    verification_url: HttpUrl | None = None
    notes: str | None = None

    @field_validator("issue_date", "expiry_date", mode="before")
    @classmethod
    def normalize_dates(cls, value: object) -> str | None:
        return normalize_partial_date(value)

    @model_validator(mode="after")
    def validate_dates(self) -> "CertificationCreate":
        if self.issue_date is not None:
            validate_partial_date_range(
                self.issue_date,
                self.expiry_date,
                start_label="issue date",
                end_label="Expiry date",
            )
        return self


class CertificationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=250)
    issuer: str | None = Field(default=None, max_length=250)
    credential_id: str | None = Field(default=None, max_length=200)
    issue_date: str | None = None
    expiry_date: str | None = None
    verification_url: HttpUrl | None = None
    notes: str | None = None

    @field_validator("issue_date", "expiry_date", mode="before")
    @classmethod
    def normalize_dates(cls, value: object) -> str | None:
        return normalize_partial_date(value)

    @model_validator(mode="after")
    def validate_patch(self) -> "CertificationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        if self.issue_date is not None and self.expiry_date is not None:
            validate_partial_date_range(
                self.issue_date,
                self.expiry_date,
                start_label="issue date",
                end_label="Expiry date",
            )
        return self


class CertificationResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID
    name: str
    issuer: str | None
    credential_id: str | None
    issue_date: str | None
    expiry_date: str | None
    verification_url: str | None
    notes: str | None
