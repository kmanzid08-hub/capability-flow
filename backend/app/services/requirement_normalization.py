import re
from typing import Any

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
_SPLIT_RE = re.compile(r"\s*(?:,|;|\bor\b)\s*", re.IGNORECASE)
_AND_RE = re.compile(r"\s+and\s+", re.IGNORECASE)


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


def _infer_operator(label: str, targets: list[str], current: str) -> str:
    if len(targets) <= 1:
        return "match"
    cleaned_label = _RELATED_SUFFIX_RE.sub("", label).lower()
    if re.search(r"\bor\b", cleaned_label):
        return "one_of"
    if re.search(r"\band\b", cleaned_label):
        return "all_of"
    return current if current in {"one_of", "all_of"} else "one_of"


def normalize_requirement_fields(requirement: Any) -> tuple[str | None, list[str] | None, str]:
    """Backfill missing semantic targets without overriding explicit AI extraction."""

    existing_value = getattr(requirement, "normalized_value", None)
    existing_values = list(getattr(requirement, "values", None) or [])
    operator = str(getattr(requirement, "operator", "match") or "match")
    if existing_value or existing_values:
        explicit_targets = ([existing_value] if existing_value else []) + existing_values
        return (
            existing_value,
            existing_values or None,
            _infer_operator(
                str(getattr(requirement, "label", "") or ""),
                explicit_targets,
                operator,
            ),
        )

    label = str(getattr(requirement, "label", "") or "").strip()
    requirement_type = getattr(requirement, "requirement_type", None)
    type_name = getattr(requirement_type, "value", requirement_type)
    type_name = str(type_name or "").lower()

    targets: list[str] = []
    if type_name == "education":
        targets = _education_targets(label)
    elif type_name in {"experience", "project_experience"}:
        targets = _experience_targets(label)

    if not targets:
        return None, None, operator
    if len(targets) == 1:
        return targets[0], None, "match"
    return None, targets, _infer_operator(label, targets, operator)
