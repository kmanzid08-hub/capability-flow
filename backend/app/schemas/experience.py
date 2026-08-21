import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import AuditFields

EmploymentType = Literal[
    "full_time",
    "part_time",
    "contract",
    "consulting",
    "temporary",
    "internship",
    "volunteer",
    "other",
]


class EmploymentCreate(BaseModel):
    employer_name: str = Field(
        min_length=1,
        max_length=250,
    )

    job_title: str = Field(
        min_length=1,
        max_length=250,
    )

    employment_type: EmploymentType | None = None

    industry: str | None = Field(
        default=None,
        max_length=150,
    )

    location: str | None = Field(
        default=None,
        max_length=250,
    )

    country: str | None = Field(
        default=None,
        max_length=100,
    )

    start_date: date
    end_date: date | None = None
    is_current: bool = False

    description: str | None = None
    responsibilities: str | None = None
    achievements: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "EmploymentCreate":
        if self.is_current and self.end_date is not None:
            raise ValueError("Current employment cannot have an end date")

        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")

        return self


class EmploymentUpdate(BaseModel):
    employer_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )

    job_title: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )

    employment_type: EmploymentType | None = None

    industry: str | None = Field(
        default=None,
        max_length=150,
    )

    location: str | None = Field(
        default=None,
        max_length=250,
    )

    country: str | None = Field(
        default=None,
        max_length=100,
    )

    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None

    description: str | None = None
    responsibilities: str | None = None
    achievements: str | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "EmploymentUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")

        return self


class EmploymentResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID

    employer_name: str
    job_title: str
    employment_type: str | None
    industry: str | None
    location: str | None
    country: str | None

    start_date: date
    end_date: date | None
    is_current: bool

    description: str | None
    responsibilities: str | None
    achievements: str | None


class ProjectCreate(BaseModel):
    project_name: str = Field(
        min_length=1,
        max_length=300,
    )

    client_name: str | None = Field(
        default=None,
        max_length=250,
    )

    role: str = Field(
        min_length=1,
        max_length=250,
    )

    sector: str | None = Field(
        default=None,
        max_length=150,
    )

    location: str | None = Field(
        default=None,
        max_length=250,
    )

    country: str | None = Field(
        default=None,
        max_length=100,
    )

    start_date: date
    end_date: date | None = None
    is_current: bool = False

    description: str | None = None
    responsibilities: str | None = None
    outcomes: str | None = None
    skills_summary: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectCreate":
        if self.is_current and self.end_date is not None:
            raise ValueError("Current project cannot have an end date")

        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")

        return self


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=300,
    )

    client_name: str | None = Field(
        default=None,
        max_length=250,
    )

    role: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )

    sector: str | None = Field(
        default=None,
        max_length=150,
    )

    location: str | None = Field(
        default=None,
        max_length=250,
    )

    country: str | None = Field(
        default=None,
        max_length=100,
    )

    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None

    description: str | None = None
    responsibilities: str | None = None
    outcomes: str | None = None
    skills_summary: str | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "ProjectUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")

        return self


class ProjectResponse(AuditFields):
    organization_id: uuid.UUID
    person_id: uuid.UUID

    project_name: str
    client_name: str | None
    role: str
    sector: str | None
    location: str | None
    country: str | None

    start_date: date
    end_date: date | None
    is_current: bool

    description: str | None
    responsibilities: str | None
    outcomes: str | None
    skills_summary: str | None
