from types import SimpleNamespace

from app.models.opportunity_enums import RequirementType
from app.services.requirement_normalization import (
    normalize_requirement_fields,
    normalize_requirement_minimum_count,
    normalize_requirement_type,
)


def _req(kind: str, label: str, **overrides: object) -> SimpleNamespace:
    payload = {
        "requirement_type": SimpleNamespace(value=kind),
        "label": label,
        "normalized_value": None,
        "values": None,
        "operator": "match",
        "minimum_count": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_source_label_overrides_overbroad_ai_education_target() -> None:
    value, values, operator = normalize_requirement_fields(
        _req(
            "education",
            (
                "PhD/Master's in Agricultural Economics, Development Economics, "
                "Rural Development or related field"
            ),
            normalized_value="Economics",
        )
    )
    assert value is None
    assert values == [
        "Agricultural Economics",
        "Development Economics",
        "Rural Development",
    ]
    assert operator == "one_of"


def test_slash_separated_education_disciplines_are_alternatives() -> None:
    value, values, operator = normalize_requirement_fields(
        _req(
            "education",
            "Master's in Animal Science/Livestock Production/Veterinary Medicine",
        )
    )
    assert value is None
    assert values == ["Animal Science", "Livestock Production", "Veterinary Medicine"]
    assert operator == "one_of"


def test_similar_assignment_certificates_are_documents_not_credentials() -> None:
    requirement = _req(
        "certification",
        "At least 3 similar assignment certificates as Team Leader",
    )
    assert normalize_requirement_type(requirement) == RequirementType.DOCUMENT
    assert normalize_requirement_minimum_count(requirement) == 3
    value, values, operator = normalize_requirement_fields(requirement)
    assert value == "Team Leader"
    assert values is None
    assert operator == "match"


def test_professional_certification_remains_certification() -> None:
    requirement = _req("certification", "PMP certification")
    assert normalize_requirement_type(requirement) == RequirementType.CERTIFICATION
