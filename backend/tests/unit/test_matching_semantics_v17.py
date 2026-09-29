import uuid
from types import SimpleNamespace

from app.models.opportunity_enums import MatchStatus, RequirementImportance, RequirementType
from app.services.matching import MatchingEngine, PersonProfile
from app.services.matching_semantics import (
    role_relevance,
    semantic_strength,
    unique_duration_months,
)
from app.services.team_optimizer import RoleCandidateSet, TeamOptimizer


def _requirement(**overrides: object) -> SimpleNamespace:
    data: dict[str, object] = {
        "id": uuid.uuid4(),
        "requirement_type": RequirementType.EXPERIENCE,
        "importance": RequirementImportance.MANDATORY,
        "label": "Minimum 10 years leading impact evaluations and economic analyses",
        "normalized_value": None,
        "values_json": ["impact evaluations", "economic analyses"],
        "minimum_years": 10.0,
        "minimum_count": None,
        "minimum_degree_level": None,
        "operator": "all_of",
        "weight": 3.0,
        "evidence_required": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _profile(*, education=None, employment=None, projects=None, title="Consultant", summary=None):
    person = SimpleNamespace(
        id=uuid.uuid4(),
        professional_title=title,
        summary=summary,
        availability_status=SimpleNamespace(value="available"),
        display_name="Test Person",
        country_of_residence=None,
        nationality=None,
    )
    return PersonProfile(
        person=person,
        skills=[],
        education=education or [],
        certifications=[],
        employment=employment or [],
        projects=projects or [],
        documents=[],
    )


def test_specific_requirement_does_not_accept_generic_subset() -> None:
    assert semantic_strength("Economics", "Agricultural Economics") < 0.75
    assert semantic_strength("Agricultural Economics", "Economics") >= 0.88


def test_true_domain_synonym_is_recognized() -> None:
    assert semantic_strength("Agribusiness Economics", "Agricultural Economics") >= 0.88
    assert semantic_strength("Impact Assessment", "Impact Evaluation") >= 0.88
    assert (
        semantic_strength("Led impact evaluation and economic analysis.", "economic analyses")
        >= 0.88
    )


def test_overlapping_experience_is_counted_once() -> None:
    months = unique_duration_months(
        [
            ("2018-01", "2022-01"),
            ("2020-01", "2024-01"),
            ("2024-01", "2025-01"),
        ]
    )
    assert months == 84


def test_education_requires_specific_discipline_not_only_degree_level() -> None:
    engine = MatchingEngine(None, uuid.uuid4())  # type: ignore[arg-type]
    education = [
        SimpleNamespace(
            id=uuid.uuid4(),
            degree_level=SimpleNamespace(value="master"),
            degree_name="Master of Science in Economics",
            field_of_study="Economics",
            institution="Example University",
        )
    ]
    result = engine.evaluate_requirement(
        _profile(education=education),
        _requirement(
            requirement_type=RequirementType.EDUCATION,
            label="Master's in Agricultural Economics",
            normalized_value="Agricultural Economics",
            values_json=None,
            minimum_degree_level="master",
            minimum_years=None,
            operator="match",
        ),
    )
    assert result.status == MatchStatus.MISSING
    assert result.score <= 0.15


def test_all_of_experience_requires_every_dimension() -> None:
    engine = MatchingEngine(None, uuid.uuid4())  # type: ignore[arg-type]
    employment = [
        SimpleNamespace(
            job_title="Survey Data Analyst",
            industry="Research",
            description="Designed surveys and managed data quality.",
            responsibilities="Survey sampling and data management",
            achievements=None,
            employer_name="Example",
            start_date="2010-01",
            end_date="2024-01",
        )
    ]
    result = engine.evaluate_requirement(_profile(employment=employment), _requirement())
    assert result.status in {MatchStatus.MISSING, MatchStatus.UNVERIFIED}
    assert result.status != MatchStatus.MATCHED


def test_undated_relevant_project_prevents_false_hard_rejection() -> None:
    engine = MatchingEngine(None, uuid.uuid4())  # type: ignore[arg-type]
    projects = [
        SimpleNamespace(
            project_name="National agricultural impact assessment",
            role="Lead Agricultural Economist",
            sector="Agriculture",
            description="Led impact evaluation and economic analysis of farm livelihoods.",
            responsibilities="Team leadership, impact assessment, economic analysis",
            outcomes="Policy recommendations",
            skills_summary="Agricultural economics; impact evaluation",
            client_name="Public agency",
            start_date=None,
            end_date=None,
        )
    ]
    result = engine.evaluate_requirement(_profile(projects=projects), _requirement())
    assert result.status == MatchStatus.UNVERIFIED
    assert result.score >= 0.5


def test_role_relevance_uses_domain_history_not_only_current_title() -> None:
    relevant = role_relevance(
        "Team Leader / Agricultural Economist",
        professional_title="Consultant",
        summary="Agricultural economist working on rural development.",
        employment_titles=["Agricultural Economist", "Team Leader"],
        project_roles=["Lead Consultant"],
    )
    unrelated = role_relevance(
        "Team Leader / Agricultural Economist",
        professional_title="Petroleum Data Analyst",
        summary="Statistics and petroleum market analytics.",
        employment_titles=["Statistician", "Data Analyst"],
        project_roles=["Survey Coordinator"],
    )
    assert relevant > unrelated
    assert relevant >= 0.75


def _candidate(person_id: int, score: float) -> SimpleNamespace:
    return SimpleNamespace(
        person=SimpleNamespace(id=person_id),
        score=score,
        mandatory_failed=False,
        mandatory_unverified=False,
    )


def test_team_optimizer_can_use_candidate_beyond_old_top_eight_cutoff() -> None:
    candidates = [_candidate(index, 100.0 - index) for index in range(1, 10)]
    role_sets = [
        RoleCandidateSet(f"role-{index}", f"Role {index}", 1, candidates) for index in range(9)
    ]
    options = TeamOptimizer().build(role_sets, 1)
    assert options
    assert len(options[0].assignments) == 9
    assert len({assignment.candidate.person.id for assignment in options[0].assignments}) == 9
