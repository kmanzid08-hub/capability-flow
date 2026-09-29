import uuid
from types import SimpleNamespace

from app.models.opportunity_enums import MatchStatus, RequirementImportance, RequirementType
from app.services.matching import MatchingEngine, PersonProfile
from app.services.matching_semantics import role_relevance


def _profile(*, documents=None, projects=None, education=None, skills=None, title="Consultant"):
    person = SimpleNamespace(
        id=uuid.uuid4(),
        professional_title=title,
        summary=None,
        availability_status=SimpleNamespace(value="available"),
        display_name="Test Person",
        country_of_residence=None,
        nationality=None,
    )
    return PersonProfile(
        person=person,
        skills=skills or [],
        education=education or [],
        certifications=[],
        employment=[],
        projects=projects or [],
        documents=documents or [],
    )


def _document_requirement(count: int = 3) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        requirement_type=RequirementType.DOCUMENT,
        importance=RequirementImportance.MANDATORY,
        label=f"At least {count} similar assignment certificates as Team Leader",
        normalized_value="Team Leader",
        values_json=None,
        minimum_years=None,
        minimum_count=count,
        minimum_degree_level=None,
        operator="match",
        weight=3.0,
        evidence_required=True,
    )


def test_missing_assignment_certificate_is_verification_issue_not_confirmed_gap() -> None:
    engine = MatchingEngine(None, uuid.uuid4())  # type: ignore[arg-type]
    project = SimpleNamespace(
        project_name="National impact assessment",
        role="Team Leader",
        sector="Agriculture",
        description="Led the assignment.",
        responsibilities="Team leadership",
        outcomes=None,
        skills_summary=None,
        start_date="2023-01",
        end_date="2023-12",
    )
    result = engine.evaluate_requirement(
        _profile(projects=[project]),
        _document_requirement(),
    )
    assert result.status == MatchStatus.UNVERIFIED
    assert result.score >= 0.6


def test_assignment_certificate_count_can_be_confirmed_from_linked_documents() -> None:
    engine = MatchingEngine(None, uuid.uuid4())  # type: ignore[arg-type]
    documents = [
        SimpleNamespace(
            title=f"Team Leader completion certificate {index}",
            description="Certificate for Team Leader assignment",
            original_filename=f"team-leader-certificate-{index}.pdf",
            education_id=None,
            certification_id=None,
        )
        for index in range(3)
    ]
    result = engine.evaluate_requirement(
        _profile(documents=documents),
        _document_requirement(),
    )
    assert result.status == MatchStatus.MATCHED
    assert result.score == 1.0


def test_role_relevance_uses_structured_domain_evidence_for_generic_titles() -> None:
    statistics = role_relevance(
        "Statistician / Data Analyst",
        professional_title="Lecturer",
        summary=None,
        employment_titles=["Lecturer"],
        project_roles=[],
        education_fields=["Applied Statistics"],
        skill_names=["Data Analysis"],
    )
    unrelated = role_relevance(
        "Statistician / Data Analyst",
        professional_title="Procurement Officer",
        summary=None,
        employment_titles=["Procurement Officer"],
        project_roles=[],
        education_fields=["Supply Chain Management"],
        skill_names=["Procurement"],
    )
    assert statistics > unrelated
