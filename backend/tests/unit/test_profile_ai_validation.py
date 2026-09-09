from app.schemas.experience import ProjectCreate
from app.services.profile_ai import ProfileAIService


def test_normalize_date_value_keeps_partial_date_for_review() -> None:
    assert ProfileAIService._normalize_date_value("2020") == "2020"
    assert ProfileAIService._normalize_date_value("2020-05") == "2020-05"


def test_normalize_date_value_strips_time_from_explicit_iso_date() -> None:
    assert ProfileAIService._normalize_date_value("2020-05-17T00:00:00Z") == "2020-05-17"


def test_normalize_employment_type_drops_unsupported_value() -> None:
    payload = ProfileAIService._normalize_experience_payload(
        {
            "start_date": "2020-05-17",
            "end_date": None,
            "is_current": False,
            "employment_type": "academic",
        },
        "employment",
    )
    assert payload["employment_type"] is None


def test_partial_start_date_is_accepted() -> None:
    project = ProjectCreate.model_validate(
        {
            "project_name": "Example",
            "role": "Lead",
            "start_date": "2020",
            "end_date": "2021-01",
            "is_current": False,
        }
    )

    assert project.start_date == "2020"
    assert project.end_date == "2021-01"


def test_short_meaningful_document_text_is_usable() -> None:
    assert (
        ProfileAIService._has_usable_fallback_text(
            "Emmanuel M. MUNYAMAHORO - Market analysis Expert"
        )
        is True
    )


def test_tiny_document_fragment_is_not_usable() -> None:
    assert ProfileAIService._has_usable_fallback_text("Page 1") is False
