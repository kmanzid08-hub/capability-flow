from enum import StrEnum


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    DATA_ENTRY = "data_entry"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class AvailabilityStatus(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    PARTIALLY_AVAILABLE = "partially_available"
    UNAVAILABLE = "unavailable"


class ProfileStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SkillProficiency(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class DegreeLevel(StrEnum):
    SECONDARY = "secondary"
    CERTIFICATE = "certificate"
    DIPLOMA = "diploma"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"
    PROFESSIONAL = "professional"
    OTHER = "other"


class DocumentType(StrEnum):
    CV = "cv"
    CERTIFICATE = "certificate"
    DEGREE = "degree"
    GOOD_COMPLETION_CERTIFICATE = "good_completion_certificate"
    REFERENCE_LETTER = "reference_letter"
    LICENSE = "license"
    PROJECT_EVIDENCE = "project_evidence"
    EMPLOYMENT_EVIDENCE = "employment_evidence"
    REPORT = "report"
    CONTRACT = "contract"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    IMAGE = "image"
    OTHER = "other"
