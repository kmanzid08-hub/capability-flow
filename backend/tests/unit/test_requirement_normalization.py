from types import SimpleNamespace

from app.services.requirement_normalization import normalize_requirement_fields


def _req(kind: str, label: str, **overrides: object) -> SimpleNamespace:
    payload = {
        "requirement_type": SimpleNamespace(value=kind),
        "label": label,
        "normalized_value": None,
        "values": None,
        "operator": "match",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_education_backfill_preserves_specific_disciplines() -> None:
    value, values, operator = normalize_requirement_fields(
        _req(
            "education",
            (
                "PhD/Master's in Agricultural Economics, Development Economics, "
                "Rural Development or related field"
            ),
        )
    )
    assert value is None
    assert values == [
        "Agricultural Economics",
        "Development Economics",
        "Rural Development",
    ]
    assert operator == "one_of"


def test_experience_backfill_does_not_reduce_to_total_career_years() -> None:
    value, values, operator = normalize_requirement_fields(
        _req(
            "experience",
            "Minimum 10 years leading impact evaluations and economic analyses",
        )
    )
    assert value is None
    assert values == ["impact evaluations", "economic analyses"]
    assert operator == "one_of"


def test_existing_machine_targets_are_never_overwritten() -> None:
    value, values, operator = normalize_requirement_fields(
        _req(
            "education",
            "Master's in Agricultural Economics",
            normalized_value="Agricultural Economics",
        )
    )
    assert value == "Agricultural Economics"
    assert values is None
    assert operator == "match"


def test_nonsemantic_requirement_types_are_not_guessed_from_labels() -> None:
    value, values, operator = normalize_requirement_fields(
        _req("skill", "At least 5 years using statistical software such as STATA")
    )
    assert value is None
    assert values is None
    assert operator == "match"
