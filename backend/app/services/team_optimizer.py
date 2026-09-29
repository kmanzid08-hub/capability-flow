from dataclasses import dataclass

from app.services.matching import CandidateEvaluation


@dataclass(frozen=True)
class RoleCandidateSet:
    role_id: object
    role_title: str
    quantity: int
    candidates: list[CandidateEvaluation]


@dataclass(frozen=True)
class TeamAssignment:
    role_id: object
    role_title: str
    candidate: CandidateEvaluation


@dataclass(frozen=True)
class TeamOption:
    score: float
    assignments: list[TeamAssignment]
    mandatory_constraints_satisfied: bool


class TeamOptimizer:
    """Bounded beam search for globally coherent team composition.

    The previous Cartesian search considered only the top eight candidates per role. That
    can exclude a valid team when several roles compete for the same people. Beam search
    keeps the search bounded while allowing candidates deeper in each role ranking to solve
    those conflicts.
    """

    candidate_depth = 40
    beam_width = 1200

    def build(
        self,
        role_sets: list[RoleCandidateSet],
        max_options: int | None = 3,
    ) -> list[TeamOption]:
        slots: list[tuple[object, str, list[CandidateEvaluation]]] = []
        for role_set in role_sets:
            for _ in range(role_set.quantity):
                slots.append(
                    (
                        role_set.role_id,
                        role_set.role_title,
                        role_set.candidates[: self.candidate_depth],
                    )
                )
        if not slots or any(not candidates for _, _, candidates in slots):
            return []

        # (assignments, used person ids, sum score, confirmed mandatory failures,
        # mandatory verification items)
        beam: list[tuple[list[TeamAssignment], set[object], float, int, int]] = [
            ([], set(), 0.0, 0, 0)
        ]
        for role_id, role_title, candidates in slots:
            expanded: list[tuple[list[TeamAssignment], set[object], float, int, int]] = []
            for assignments, used_ids, score_sum, failures, unverified in beam:
                for candidate in candidates:
                    person_id = candidate.person.id
                    if person_id in used_ids:
                        continue
                    assignment = TeamAssignment(role_id, role_title, candidate)
                    expanded.append(
                        (
                            [*assignments, assignment],
                            {*used_ids, person_id},
                            score_sum + candidate.score,
                            failures + int(candidate.mandatory_failed),
                            unverified + int(candidate.mandatory_unverified),
                        )
                    )
            if not expanded:
                return []
            slot_count = len(expanded[0][0])
            expanded.sort(
                key=lambda item: (
                    -item[3],
                    -item[4],
                    item[2] / slot_count,
                ),
                reverse=True,
            )
            beam = expanded[: self.beam_width]

        options = [
            TeamOption(
                score=round(score_sum / len(assignments), 2),
                assignments=assignments,
                mandatory_constraints_satisfied=failures == 0,
            )
            for assignments, _, score_sum, failures, _ in beam
        ]
        options.sort(
            key=lambda item: (item.mandatory_constraints_satisfied, item.score),
            reverse=True,
        )
        return options if max_options is None else options[:max_options]
