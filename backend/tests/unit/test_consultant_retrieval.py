import uuid
from types import SimpleNamespace
from typing import cast

from app.services.consultant_retrieval import (
    evidence_records,
    query_terms,
    summarize_shadow_recall,
)
from app.services.matching import PersonProfile


def _record(**fields: object) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), **fields)


def test_index_contains_individual_evidence_not_contact_details() -> None:
    person_id = uuid.uuid4()
    profile = cast(
        PersonProfile,
        SimpleNamespace(
            person=SimpleNamespace(
                id=person_id,
                primary_email="confidential@example.org",
                primary_phone="+250 700 000 000",
                display_name="Test Person",
            ),
            skills=[_record(name="Soil testing", notes="Laboratory analysis", years_experience=4)],
            education=[
                _record(
                    degree_level=SimpleNamespace(value="master"),
                    degree_name="MSc", field_of_study="Agricultural Economics",
                )
            ],
            certifications=[],
            employment=[],
            projects=[
                _record(
                    project_name="Soil quality survey", role="Analyst", sector="Agriculture",
                    description="Soil sampling", responsibilities=None, outcomes=None,
                    skills_summary=None, country="Rwanda",
                )
            ],
        ),
    )
    records = evidence_records(profile)
    assert {item.evidence_type for item in records} == {"skill", "education", "project"}
    assert all(item.person_id == person_id for item in records)
    assert any("Agricultural Economics" in item.content for item in records)
    assert all("confidential@example.org" not in item.content for item in records)
    assert all("+250 700" not in item.content for item in records)


def test_evidence_hash_changes_with_content() -> None:
    profile = cast(
        PersonProfile,
        SimpleNamespace(
            person=SimpleNamespace(id=uuid.uuid4()),
            skills=[_record(name="Accounting", notes=None, years_experience=None)],
            education=[], certifications=[], employment=[], projects=[],
        ),
    )
    first = evidence_records(profile)[0].digest
    profile.skills[0].name = "Auditing"
    second = evidence_records(profile)[0].digest
    assert first != second


def test_query_terms_filter_boilerplate_but_preserve_specific_skills() -> None:
    terms = query_terms(
        "Consultant required with five years experience in soil testing and laboratory analysis"
    )
    assert {"soil", "testing", "laboratory", "analysis"}.issubset(terms)
    assert "consultant" not in terms
    assert "experience" not in terms


def test_shadow_recall_never_modifies_baseline_rankings() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    baseline = [a, b, c]
    assert summarize_shadow_recall(baseline, {a, c}) == (2, 3)
    assert baseline == [a, b, c]
