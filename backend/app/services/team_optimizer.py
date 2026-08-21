import itertools
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
    def build(self, role_sets: list[RoleCandidateSet], max_options: int = 3) -> list[TeamOption]:
        slots: list[tuple[object, str, list[CandidateEvaluation]]] = []
        for role_set in role_sets:
            for _ in range(role_set.quantity):
                # Keep the search bounded. Candidate ranking has already
                # done the expensive filtering.
                slots.append((role_set.role_id, role_set.role_title, role_set.candidates[:8]))
        if not slots or any(not candidates for _, _, candidates in slots):
            return []
        options: list[TeamOption] = []
        for combination in itertools.product(*(candidates for _, _, candidates in slots)):
            person_ids = [candidate.person.id for candidate in combination]
            if len(person_ids) != len(set(person_ids)):
                continue
            assignments = [
                TeamAssignment(
                    role_id=slots[index][0],
                    role_title=slots[index][1],
                    candidate=candidate,
                )
                for index, candidate in enumerate(combination)
            ]
            score = sum(item.candidate.score for item in assignments) / len(assignments)
            mandatory_ok = all(not item.candidate.mandatory_failed for item in assignments)
            if not mandatory_ok:
                score = min(score, 79.0)
            options.append(TeamOption(round(score, 2), assignments, mandatory_ok))
        options.sort(
            key=lambda item: (item.mandatory_constraints_satisfied, item.score),
            reverse=True,
        )
        return options[:max_options]
