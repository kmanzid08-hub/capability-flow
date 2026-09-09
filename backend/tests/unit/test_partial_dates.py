import pytest

from app.core.partial_dates import (
    PartialDateError,
    months_between_partial,
    normalize_partial_date,
    validate_partial_date_range,
)
from app.schemas.experience import EmploymentCreate, ProjectCreate


def test_normalizes_supported_partial_date_precisions() -> None:
    assert normalize_partial_date("2020") == "2020"
    assert normalize_partial_date("2021-01") == "2021-01"
    assert normalize_partial_date("2023-08-17") == "2023-08-17"


def test_normalizes_common_unambiguous_date_forms() -> None:
    assert normalize_partial_date("Jan 2021") == "2021-01"
    assert normalize_partial_date("01/2021") == "2021-01"
    assert normalize_partial_date("17 May 2023") == "2023-05-17"


def test_rejects_ambiguous_date_text() -> None:
    with pytest.raises(PartialDateError):
        normalize_partial_date("early 2021")


def test_experience_schemas_accept_year_and_month_precision() -> None:
    employment = EmploymentCreate.model_validate(
        {
            "employer_name": "Example",
            "job_title": "Lecturer",
            "start_date": "2020",
            "end_date": "2021-01",
            "is_current": False,
        }
    )
    project = ProjectCreate.model_validate(
        {
            "project_name": "Example Project",
            "role": "Advisor",
            "start_date": "2019",
            "end_date": "2023-08",
            "is_current": False,
        }
    )

    assert employment.start_date == "2020"
    assert employment.end_date == "2021-01"
    assert project.start_date == "2019"
    assert project.end_date == "2023-08"


def test_definitely_inverted_partial_date_range_is_rejected() -> None:
    with pytest.raises(PartialDateError):
        validate_partial_date_range("2022", "2021-12")


def test_same_year_mixed_precision_is_not_falsely_rejected() -> None:
    validate_partial_date_range("2021-12", "2021")


def test_partial_duration_uses_neutral_representative_dates() -> None:
    assert months_between_partial("2020", "2021") == 12
    assert months_between_partial("2020-05", "2021-05") == 12
