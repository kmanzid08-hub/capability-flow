import uuid
from types import SimpleNamespace

from app.models.opportunity_enums import MatchStatus, RequirementImportance, RequirementType
from app.services.matching import CandidateEvaluation, RequirementEvaluation
from app.services.opportunities import OpportunityService
from app.services.requirement_extraction import GeminiRequirementExtractor
from app.services.team_optimizer import RoleCandidateSet, TeamAssignment, TeamOptimizer


def _candidate(
    *,
    score: float = 100.0,
    mandatory_failed: bool = False,
    mandatory_unverified: bool = False,
) -> CandidateEvaluation:
    return CandidateEvaluation(
        person=SimpleNamespace(id=uuid.uuid4()),
        score=score,
        mandatory_pass_rate=0.0 if mandatory_failed else 1.0,
        preferred_pass_rate=1.0,
        mandatory_failed=mandatory_failed,
        mandatory_unverified=mandatory_unverified,
        requirement_results={},
    )


def _team_requirement(*, minimum_count: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        importance=RequirementImportance.MANDATORY,
        requirement_type=RequirementType.CUSTOM,
        label="At least one team member must provide specialist evidence",
        normalized_value="specialist evidence",
        values_json=None,
        minimum_years=None,
        minimum_count=minimum_count,
        operator="match",
        weight=3.0,
    )


class _MatchingStub:
    def __init__(self, result: RequirementEvaluation) -> None:
        self.result = result

    def evaluate_requirement(
        self,
        profile: object,
        requirement: object,
    ) -> RequirementEvaluation:
        return self.result


def _service_with_result(result: RequirementEvaluation) -> OpportunityService:
    service = OpportunityService.__new__(OpportunityService)
    service.matching = _MatchingStub(result)  # type: ignore[assignment]
    return service


def test_team_optimizer_keeps_role_fit_score_separate_from_compliance() -> None:
    candidate = _candidate(score=96.0, mandatory_failed=True)
    options = TeamOptimizer().build(
        [
            RoleCandidateSet(
                role_id=uuid.uuid4(),
                role_title="Required expert",
                quantity=1,
                candidates=[candidate],
            )
        ]
    )

    assert len(options) == 1
    assert options[0].score == 96.0
    assert options[0].mandatory_constraints_satisfied is False


def test_unverified_team_requirement_is_not_a_confirmed_gap() -> None:
    candidate = _candidate()
    service = _service_with_result(
        RequirementEvaluation(
            MatchStatus.UNVERIFIED,
            0.5,
            [],
            "Evidence requires review.",
        )
    )
    assessment = service._assess_team_constraints(
        [
            TeamAssignment(
                role_id=uuid.uuid4(),
                role_title="Expert",
                candidate=candidate,
            )
        ],
        [_team_requirement()],
        {candidate.person.id: SimpleNamespace()},
    )

    assert assessment.fully_satisfied is False
    assert assessment.needs_verification is True
    assert assessment.confirmed_gap_labels == ()
    assert assessment.unverified_labels == (
        "At least one team member must provide specialist evidence",
    )


def test_partial_team_requirement_is_a_confirmed_mandatory_gap() -> None:
    candidate = _candidate()
    service = _service_with_result(
        RequirementEvaluation(
            MatchStatus.PARTIAL,
            0.8,
            [],
            "Only part of the mandatory requirement is supported.",
        )
    )
    assessment = service._assess_team_constraints(
        [
            TeamAssignment(
                role_id=uuid.uuid4(),
                role_title="Expert",
                candidate=candidate,
            )
        ],
        [_team_requirement()],
        {candidate.person.id: SimpleNamespace()},
    )

    assert assessment.fully_satisfied is False
    assert assessment.needs_verification is False
    assert assessment.confirmed_gap_labels == (
        "At least one team member must provide specialist evidence",
    )


def test_duplicate_single_person_team_requirement_is_removed() -> None:
    duplicate = {
        "requirement_type": "skill",
        "importance": "mandatory",
        "label": "Cost-benefit analysis",
        "normalized_value": "cost-benefit analysis",
        "minimum_years": None,
        "operator": "match",
    }
    payload = {
        "roles": [
            {
                "title": "Team Leader",
                "requirements": [dict(duplicate)],
            }
        ],
        "team_requirements": [
            {
                **duplicate,
                "minimum_count": 1,
            }
        ],
    }

    cleaned = GeminiRequirementExtractor._remove_redundant_team_requirements(payload)

    assert cleaned["team_requirements"] == []


def test_true_multi_person_team_requirement_is_preserved() -> None:
    duplicate = {
        "requirement_type": "skill",
        "importance": "mandatory",
        "label": "Cost-benefit analysis",
        "normalized_value": "cost-benefit analysis",
        "minimum_years": None,
        "operator": "match",
    }
    payload = {
        "roles": [
            {
                "title": "Team Leader",
                "requirements": [dict(duplicate)],
            }
        ],
        "team_requirements": [
            {
                **duplicate,
                "minimum_count": 2,
            }
        ],
    }

    cleaned = GeminiRequirementExtractor._remove_redundant_team_requirements(payload)

    assert len(cleaned["team_requirements"]) == 1
    assert cleaned["team_requirements"][0]["minimum_count"] == 2
