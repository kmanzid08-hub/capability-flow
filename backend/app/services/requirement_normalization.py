import re
from typing import Any

from app.models.opportunity_enums import RequirementType

_RELATED_SUFFIX_RE = re.compile(
    r"(?:,?\s*(?:or|and)\s+)?(?:a\s+)?(?:closely\s+)?(?:related|relevant|equivalent)\s+"
    r"(?:field|discipline|subject|area)(?:s)?\.?$",
    re.IGNORECASE,
)
_DEGREE_PREFIX_RE = re.compile(
    r"^.*?\b(?:ph\.?d\.?|doctorate|doctoral|master(?:'s|s)?|msc|m\.?sc\.?|mba|"
    r"bachelor(?:'s|s)?|bsc|b\.?sc\.?)\b[^\n]*?\b(?:in|of)\s+",
    re.IGNORECASE,
)
_YEARS_PREFIX_RE = re.compile(
    r"^.*?\b(?:minimum\s+|at\s+least\s+|more\s+than\s+|over\s+)?\d+(?:\.\d+)?\+?\s+"
    r"years?\b(?:\s+of)?\s*",
    re.IGNORECASE,
)
_LEADING_ACTIVITY_RE = re.compile(
    r"^(?:experience\s+in\s+|with\s+experience\s+in\s+|leading\s+|conducting\s+|"
    r"undertaking\s+|performing\s+|carrying\s+out\s+|managing\s+|working\s+on\s+)",
    re.IGNORECASE,
)
_SPLIT_RE = re.compile(r"\s*(?:,|;|/|\bor\b)\s*", re.IGNORECASE)
_AND_RE = re.compile(r"\s+and\s+", re.IGNORECASE)
_COUNT_RE = re.compile(
    r"\b(?:at\s+least|minimum(?:\s+of)?|no\s+fewer\s+than)?\s*(\d+)\s+"
    r"(?:similar\s+)?(?:assignment\s+)?(?:certificate|certificates|reference|references|"
    r"letter|letters|document|documents)\b",
    re.IGNORECASE,
)
_DOCUMENT_EVIDENCE_RE = re.compile(
    r"\b(?:similar\s+assignment\s+certificates?|certificates?\s+of\s+(?:good\s+)?completion|"
    r"completion\s+certificates?|reference\s+letters?|client\s+references?|"
    r"proof\s+of\s+(?:similar\s+)?assignments?|documentary\s+evidence|supporting\s+documents?)\b",
    re.IGNORECASE,
)


def _clean(value: str) -> str:
    value = " ".join(value.replace("/", " / ").split()).strip(" .,:;-–—")
    value = _RELATED_SUFFIX_RE.sub("", value).strip(" .,:;-–—")
    return value


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _education_targets(label: str) -> list[str]:
    subject = _DEGREE_PREFIX_RE.sub("", label).strip()
    if subject == label.strip():
        match = re.search(r"\b(?:in|of)\s+(.+)$", label, re.IGNORECASE)
        subject = match.group(1) if match else ""
    subject = _clean(subject)
    if not subject:
        return []
    parts = _SPLIT_RE.split(subject)
    expanded: list[str] = []
    for part in parts:
        part = _clean(part)
        if not part:
            continue
        and_parts = [_clean(item) for item in _AND_RE.split(part)]
        if len(and_parts) == 2 and all(len(item.split()) >= 2 for item in and_parts):
            expanded.extend(and_parts)
        else:
            expanded.append(part)
    return _dedupe(expanded)


def _experience_targets(label: str) -> list[str]:
    subject = _YEARS_PREFIX_RE.sub("", label).strip()
    if subject == label.strip():
        match = re.search(
            r"\b(?:experience|expertise|background)\s+(?:in|with)\s+(.+)$",
            label,
            re.IGNORECASE,
        )
        subject = match.group(1) if match else ""
    subject = _LEADING_ACTIVITY_RE.sub("", subject).strip()
    subject = _clean(subject)
    if not subject:
        return []

    parts = _SPLIT_RE.split(subject)
    expanded: list[str] = []
    for part in parts:
        part = _clean(part)
        if not part:
            continue
        and_parts = [_clean(item) for item in _AND_RE.split(part)]
        if len(and_parts) == 2 and all(len(item.split()) >= 2 for item in and_parts):
            expanded.extend(and_parts)
        else:
            expanded.append(part)
    return _dedupe(expanded)


def _document_targets(label: str) -> list[str]:
    for pattern in (
        r"\bas\s+(?:a\s+|an\s+|the\s+)?(.+)$",
        r"\bfor\s+(?:the\s+)?(?:role\s+of\s+)?(.+)$",
    ):
        match = re.search(pattern, label, re.IGNORECASE)
        if match:
            target = _clean(match.group(1))
            if target:
                return [target]
    return []


def _type_name(requirement: Any) -> str:
    requirement_type = getattr(requirement, "requirement_type", None)
    return str(getattr(requirement_type, "value", requirement_type) or "").lower()


def normalize_requirement_type(requirement: Any) -> RequirementType:
    """Correct deterministic type mistakes that would change compliance semantics."""

    label = str(getattr(requirement, "label", "") or "").strip()
    original_name = _type_name(requirement)
    if _DOCUMENT_EVIDENCE_RE.search(label):
        return RequirementType.DOCUMENT
    try:
        return RequirementType(original_name)
    except ValueError:
        return RequirementType.CUSTOM


def normalize_requirement_minimum_count(requirement: Any) -> int | None:
    existing = getattr(requirement, "minimum_count", None)
    if existing is not None:
        return int(existing)
    if normalize_requirement_type(requirement) != RequirementType.DOCUMENT:
        return None
    label = str(getattr(requirement, "label", "") or "")
    match = _COUNT_RE.search(label)
    return int(match.group(1)) if match else None


def _infer_operator(label: str, targets: list[str], current: str) -> str:
    if len(targets) <= 1:
        return "match"
    cleaned_label = _RELATED_SUFFIX_RE.sub("", label).lower()
    if re.search(r"\bor\b", cleaned_label) or "/" in cleaned_label:
        return "one_of"
    if re.search(r"\band\b", cleaned_label):
        return "all_of"
    return current if current in {"one_of", "all_of"} else "one_of"


def normalize_requirement_fields(requirement: Any) -> tuple[str | None, list[str] | None, str]:
    """Normalize machine targets using the source-facing label as the precision boundary.

    AI-provided targets remain useful for unstructured requirement types. For education and
    experience, however, deterministic targets parsed from the human-readable source label win
    whenever available. This prevents a broad AI target such as ``Economics`` from silently
    replacing ``Agricultural Economics`` in the source requirement.
    """

    label = str(getattr(requirement, "label", "") or "").strip()
    type_name = normalize_requirement_type(requirement).value
    operator = str(getattr(requirement, "operator", "match") or "match")

    derived_targets: list[str] = []
    if type_name == "education":
        derived_targets = _education_targets(label)
    elif type_name in {"experience", "project_experience"}:
        derived_targets = _experience_targets(label)
    elif type_name == "document":
        derived_targets = _document_targets(label)

    if derived_targets:
        if len(derived_targets) == 1:
            return derived_targets[0], None, "match"
        return None, derived_targets, _infer_operator(label, derived_targets, operator)

    existing_value = getattr(requirement, "normalized_value", None)
    existing_values = list(getattr(requirement, "values", None) or [])
    if existing_value or existing_values:
        explicit_targets = ([existing_value] if existing_value else []) + existing_values
        return (
            existing_value,
            existing_values or None,
            _infer_operator(
                label,
                explicit_targets,
                operator,
            ),
        )

    return None, None, operator
