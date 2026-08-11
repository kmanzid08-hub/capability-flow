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
