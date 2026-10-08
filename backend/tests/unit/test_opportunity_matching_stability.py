from types import SimpleNamespace
from typing import cast

from app.services.matching import CandidateEvaluation
from app.services.opportunities import _retain_top_candidate_evaluations
from app.services.team_optimizer import RoleCandidateSet, TeamOptimizer


def _evaluation(
    person_id: int,
    score: float,
    *,
    mandatory_failed: bool = False,
    mandatory_unverified: bool = False,
    role_relevance_score: float = 0.0,
) -> CandidateEvaluation:
    return cast(
        CandidateEvaluation,
        SimpleNamespace(
            person=SimpleNamespace(id=person_id),
            score=score,
            mandatory_pass_rate=1.0,
            preferred_pass_rate=1.0,
            mandatory_failed=mandatory_failed,
            mandatory_unverified=mandatory_unverified,
            requirement_results={},
            role_relevance_score=role_relevance_score,
        ),
    )


def test_candidate_pruning_preserves_global_top_n_across_batches() -> None:
    evaluations: list[CandidateEvaluation] = []
    for person_id, score in enumerate((10.0, 70.0, 30.0, 90.0, 20.0, 80.0, 40.0), start=1):
        evaluations.append(_evaluation(person_id, score))
        if len(evaluations) >= 4:
            _retain_top_candidate_evaluations(evaluations, 2)

    _retain_top_candidate_evaluations(evaluations, 2)

    assert [item.score for item in evaluations] == [90.0, 80.0]


def test_candidate_pruning_preserves_mandatory_ranking_priority() -> None:
    evaluations = [
        _evaluation(1, 99.0, mandatory_failed=True),
        _evaluation(2, 95.0, mandatory_unverified=True),
        _evaluation(3, 40.0),
        _evaluation(4, 30.0),
    ]

    _retain_top_candidate_evaluations(evaluations, 2)

    assert [item.score for item in evaluations] == [40.0, 30.0]


def test_team_optimizer_still_returns_best_distinct_team() -> None:
    optimizer = TeamOptimizer()
    role_sets = [
        RoleCandidateSet(
            role_id="role-a",
            role_title="Role A",
            quantity=1,
            candidates=[
                _evaluation(1, 95.0),
                _evaluation(2, 90.0),
            ],
        ),
        RoleCandidateSet(
            role_id="role-b",
            role_title="Role B",
            quantity=1,
            candidates=[
                _evaluation(1, 99.0),
                _evaluation(3, 85.0),
            ],
        ),
    ]

    options = optimizer.build(role_sets, 1)

    assert len(options) == 1
    assert [assignment.candidate.person.id for assignment in options[0].assignments] == [2, 1]
    assert options[0].score == 94.5
