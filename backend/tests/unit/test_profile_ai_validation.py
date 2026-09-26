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


def test_normalize_education_payload_preserves_partial_precision() -> None:
    payload = ProfileAIService._normalize_education_payload(
        {
            "start_year": 2016,
            "graduation_year": 2020,
            "institution": "Example University",
        }
    )

    assert payload["start_date"] == "2016"
    assert payload["graduation_date"] == "2020"
    assert "start_year" not in payload
    assert "graduation_year" not in payload


def test_normalize_certification_payload_accepts_month_precision() -> None:
    payload = ProfileAIService._normalize_evidence_date_payload(
        {"issue_date": "Apr 2020", "expiry_date": "2026"},
        ("issue_date", "expiry_date"),
    )

    assert payload["issue_date"] == "2020-04"
    assert payload["expiry_date"] == "2026"


def test_image_heavy_pdf_with_thin_text_forces_page_recovery() -> None:
    repeated_header = "\n".join(
        f"[Page {page}]\nOFFICIAL DOCUMENTS TRESOR AHADI" for page in range(1, 17)
    )

    assert ProfileAIService._pdf_text_needs_image_recovery(
        repeated_header,
        page_count=16,
        image_pages=16,
    )


def test_dense_pdf_text_does_not_force_page_recovery() -> None:
    dense_text = "\n".join(
        f"Page {page} employment education certification professional evidence " * 20
        for page in range(1, 9)
    )

    assert not ProfileAIService._pdf_text_needs_image_recovery(
        dense_text,
        page_count=8,
        image_pages=8,
    )
