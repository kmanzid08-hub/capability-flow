from enum import StrEnum


class OpportunityStatus(StrEnum):
    NEW = "new"
    ANALYZING = "analyzing"
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    PURSUING = "pursuing"
    NOT_PURSUING = "not_pursuing"
    SUBMITTED = "submitted"
    WON = "won"
    LOST = "lost"
    ARCHIVED = "archived"


class OpportunitySourceType(StrEnum):
    URL = "url"
    PASTED_TEXT = "pasted_text"
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    INTEGRATION = "integration"
    OTHER = "other"


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    FETCHING = "fetching"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    MATCHING = "matching"
    BUILDING_TEAM = "building_team"
    COMPLETE = "complete"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class RequirementType(StrEnum):
    SKILL = "skill"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    EXPERIENCE = "experience"
    PROJECT_EXPERIENCE = "project_experience"
    SECTOR = "sector"
    GEOGRAPHY = "geography"
    LANGUAGE = "language"
    AVAILABILITY = "availability"
    CLIENT_EXPERIENCE = "client_experience"
    DOCUMENT = "document"
    CUSTOM = "custom"


class RequirementImportance(StrEnum):
    MANDATORY = "mandatory"
    PREFERRED = "preferred"
    INFORMATIONAL = "informational"


class MatchStatus(StrEnum):
    MATCHED = "matched"
    PARTIAL = "partial"
    MISSING = "missing"
    UNVERIFIED = "unverified"
    NOT_APPLICABLE = "not_applicable"


class TeamStatus(StrEnum):
    RECOMMENDED = "recommended"
    SELECTED = "selected"
    REJECTED = "rejected"
