import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capability import PersonCertification, PersonEducation, PersonSkill
from app.models.document import PersonDocument
from app.models.enums import ProfileStatus
from app.models.experience import EmploymentExperience, ProjectExperience
from app.models.opportunity_enums import MatchStatus, RequirementImportance, RequirementType
from app.models.person import Person


class RequirementLike(Protocol):
    id: uuid.UUID
    requirement_type: RequirementType
    importance: RequirementImportance
    label: str
    normalized_value: str | None
    values_json: list[str] | None
    minimum_years: float | None
    minimum_count: int | None
    minimum_degree_level: str | None
    operator: str
    weight: float
    evidence_required: bool


DEGREE_RANK: dict[str, int] = {
    "secondary": 1,
    "certificate": 2,
    "diploma": 3,
    "associate": 4,
    "bachelor": 5,
    "master": 6,
    "doctorate": 7,
    "professional": 7,
    "other": 0,
}


@dataclass(frozen=True)
class Evidence:
    source: str
    label: str
    detail: str | None = None

    def as_json(self) -> dict[str, object]:
        return {"source": self.source, "label": self.label, "detail": self.detail}


@dataclass(frozen=True)
class RequirementEvaluation:
    status: MatchStatus
    score: float
    evidence: list[Evidence]
    explanation: str


@dataclass(frozen=True)
class CandidateEvaluation:
    person: Person
    score: float
    mandatory_pass_rate: float
    preferred_pass_rate: float
    mandatory_failed: bool
    mandatory_unverified: bool
    requirement_results: dict[uuid.UUID, RequirementEvaluation]


@dataclass
class PersonProfile:
    person: Person
    skills: list[PersonSkill]
    education: list[PersonEducation]
    certifications: list[PersonCertification]
    employment: list[EmploymentExperience]
    projects: list[ProjectExperience]
    documents: list[PersonDocument]


def normalize(value: str | None) -> str:
    return " ".join((value or "").lower().replace("-", " ").replace("_", " ").split())


def contains(haystack: str | None, needle: str | None) -> bool:
    """Conservative semantic-ish text matching for structured profile evidence.

    Exact normalized containment remains strongest, but token overlap and close phrasing
    prevent obvious false negatives such as ``financial management`` versus
    ``management of project finances``. This never manufactures evidence: it only
    compares text that already exists in the verified profile.
    """
    h = normalize(haystack)
    n = normalize(needle)
    if not h or not n:
        return False
    if n in h or h in n:
        return True

    h_tokens = {token for token in h.split() if len(token) > 2}
    n_tokens = {token for token in n.split() if len(token) > 2}
    if not h_tokens or not n_tokens:
        return False

    overlap = len(h_tokens & n_tokens) / len(n_tokens)
    if overlap >= 0.67:
        return True

    return SequenceMatcher(None, h, n).ratio() >= 0.82


def months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


class MatchingEngine:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    async def load_profiles(self) -> list[PersonProfile]:
        people = list(
            await self.session.scalars(
                select(Person).where(
                    Person.organization_id == self.organization_id,
                    Person.profile_status != ProfileStatus.ARCHIVED,
                )
            )
        )
        if not people:
            return []
        person_ids = [person.id for person in people]
        skills = list(
            await self.session.scalars(
                select(PersonSkill).where(PersonSkill.person_id.in_(person_ids))
            )
        )
        education = list(
            await self.session.scalars(
                select(PersonEducation).where(PersonEducation.person_id.in_(person_ids))
            )
        )
        certifications = list(
            await self.session.scalars(
                select(PersonCertification).where(PersonCertification.person_id.in_(person_ids))
            )
        )
        employment = list(
            await self.session.scalars(
                select(EmploymentExperience).where(EmploymentExperience.person_id.in_(person_ids))
            )
        )
        projects = list(
            await self.session.scalars(
                select(ProjectExperience).where(ProjectExperience.person_id.in_(person_ids))
            )
        )
        documents = list(
            await self.session.scalars(
                select(PersonDocument).where(PersonDocument.person_id.in_(person_ids))
            )
        )
        return [
            PersonProfile(
                person=person,
                skills=[item for item in skills if item.person_id == person.id],
                education=[item for item in education if item.person_id == person.id],
                certifications=[item for item in certifications if item.person_id == person.id],
                employment=[item for item in employment if item.person_id == person.id],
                projects=[item for item in projects if item.person_id == person.id],
                documents=[item for item in documents if item.person_id == person.id],
            )
            for person in people
        ]

    def evaluate(
        self,
        profile: PersonProfile,
        requirements: Sequence[RequirementLike],
    ) -> CandidateEvaluation:
        results = {req.id: self.evaluate_requirement(profile, req) for req in requirements}
        weighted_total = 0.0
        weighted_score = 0.0
        mandatory_total = 0
        mandatory_passed = 0
        preferred_total = 0
        preferred_passed = 0
        mandatory_failed = False
        mandatory_unverified = False
        for req in requirements:
            result = results[req.id]
            if req.importance == RequirementImportance.INFORMATIONAL:
                continue
            weight = max(req.weight, 0.01)
            weighted_total += weight
            weighted_score += weight * result.score
            if req.importance == RequirementImportance.MANDATORY:
                mandatory_total += 1
                if result.status == MatchStatus.MATCHED:
                    mandatory_passed += 1
                elif result.status == MatchStatus.PARTIAL and result.score >= 0.75:
                    mandatory_passed += 1
                elif result.status == MatchStatus.UNVERIFIED:
                    # Lack of verification is not proof that a qualification is absent.
                    mandatory_unverified = True
                else:
                    # Only a confirmed missing/insufficient result is a hard failure.
                    mandatory_failed = True
            elif req.importance == RequirementImportance.PREFERRED:
                preferred_total += 1
                if result.score >= 0.75:
                    preferred_passed += 1
        raw_score = 100.0 * (weighted_score / weighted_total) if weighted_total else 0.0
        # A hard requirement miss caps the score so a candidate cannot look fully compliant.
        if mandatory_failed:
            raw_score = min(raw_score, 79.0)
        return CandidateEvaluation(
            person=profile.person,
            score=round(raw_score, 2),
            mandatory_pass_rate=(
                round(mandatory_passed / mandatory_total, 4) if mandatory_total else 1.0
            ),
            preferred_pass_rate=(
                round(preferred_passed / preferred_total, 4) if preferred_total else 1.0
            ),
            mandatory_failed=mandatory_failed,
            mandatory_unverified=mandatory_unverified,
            requirement_results=results,
        )

    def evaluate_requirement(
        self, profile: PersonProfile, req: RequirementLike
    ) -> RequirementEvaluation:
        dispatch = {
            RequirementType.SKILL: self._skill,
            RequirementType.EDUCATION: self._education,
            RequirementType.CERTIFICATION: self._certification,
            RequirementType.EXPERIENCE: self._experience,
            RequirementType.PROJECT_EXPERIENCE: self._project_experience,
            RequirementType.SECTOR: self._sector,
            RequirementType.GEOGRAPHY: self._geography,
            RequirementType.CLIENT_EXPERIENCE: self._client,
            RequirementType.AVAILABILITY: self._availability,
        }
        evaluator = dispatch.get(req.requirement_type)
        if evaluator is None:
            return RequirementEvaluation(
                MatchStatus.UNVERIFIED,
                0.5,
                [],
                "This requirement needs semantic or human verification.",
            )
        return evaluator(profile, req)

    def _targets(self, req: RequirementLike) -> list[str]:
        values = req.values_json or []
        if req.normalized_value:
            values = [req.normalized_value, *values]
        return [value for value in values if value]

    def _skill(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        targets = self._targets(req)
        matches = [
            skill
            for skill in profile.skills
            if any(contains(skill.name, target) for target in targets)
        ]
        if not matches:
            # Project text is useful evidence, but it is partial because
            # it is not structured skill evidence.
            project_hits = [
                project
                for project in profile.projects
                if any(contains(project.skills_summary, target) for target in targets)
            ]
            if project_hits:
                return RequirementEvaluation(
                    MatchStatus.PARTIAL,
                    0.65,
                    [
                        Evidence("project", item.project_name, item.skills_summary)
                        for item in project_hits[:5]
                    ],
                    "The skill appears in project evidence but not as a structured skill record.",
                )
            if profile.skills or profile.projects or profile.employment:
                return RequirementEvaluation(
                    MatchStatus.UNVERIFIED,
                    0.5,
                    [],
                    (
                        "No direct structured skill-name match was found. The person has "
                        "professional evidence that may use different terminology and needs review."
                    ),
                )
            return RequirementEvaluation(
                MatchStatus.MISSING,
                0.0,
                [],
                "No skill evidence is recorded for this person.",
            )
        best = max(matches, key=lambda skill: skill.years_experience or 0)
        years = best.years_experience or 0.0
        if req.minimum_years and years < req.minimum_years:
            ratio = min(0.9, years / req.minimum_years) if req.minimum_years else 0.0
            return RequirementEvaluation(
                MatchStatus.PARTIAL,
                max(0.25, ratio),
                [Evidence("skill", best.name, f"{years:g} years")],
                (
                    f"Skill is present, but recorded experience is {years:g} years "
                    f"vs {req.minimum_years:g} required."
                ),
            )
        return RequirementEvaluation(
            MatchStatus.MATCHED,
            1.0,
            [
                Evidence(
                    "skill",
                    best.name,
                    f"{years:g} years" if best.years_experience is not None else None,
                )
            ],
            "Structured skill evidence satisfies the requirement.",
        )

    def _education(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        min_rank = DEGREE_RANK.get(normalize(req.minimum_degree_level), 0)
        targets = self._targets(req)
        eligible = [
            item
            for item in profile.education
            if DEGREE_RANK.get(item.degree_level.value, 0) >= min_rank
            and (
                not targets
                or any(
                    contains(item.field_of_study, target) or contains(item.degree_name, target)
                    for target in targets
                )
            )
        ]
        if eligible:
            item = max(eligible, key=lambda degree: DEGREE_RANK.get(degree.degree_level.value, 0))
            linked_documents = [doc for doc in profile.documents if doc.education_id == item.id]
            if req.evidence_required and not linked_documents:
                return RequirementEvaluation(
                    MatchStatus.UNVERIFIED,
                    0.7,
                    [
                        Evidence(
                            "education",
                            item.degree_name or item.degree_level.value,
                            item.institution,
                        )
                    ],
                    (
                        "Education satisfies the requirement, but required "
                        "documentary evidence is not linked."
                    ),
                )
            evidence = [
                Evidence(
                    "education",
                    item.degree_name or item.degree_level.value,
                    item.institution,
                )
            ]
            evidence.extend(
                Evidence("document", doc.title, doc.original_filename)
                for doc in linked_documents[:3]
            )
            return RequirementEvaluation(
                MatchStatus.MATCHED,
                1.0,
                evidence,
                "Education level and field satisfy the requirement"
                + (" with linked documentary evidence." if linked_documents else "."),
            )
        level_only = [
            item
            for item in profile.education
            if DEGREE_RANK.get(item.degree_level.value, 0) >= min_rank
        ]
        if level_only and targets:
            item = level_only[0]
            return RequirementEvaluation(
                MatchStatus.UNVERIFIED,
                0.65,
                [
                    Evidence(
                        "education",
                        item.degree_name or item.degree_level.value,
                        item.field_of_study,
                    )
                ],
                "Required degree level is present, but the field is not an explicit match.",
            )
        return RequirementEvaluation(
            MatchStatus.MISSING,
            0.0,
            [],
            "No qualifying education record found.",
        )

    def _certification(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        targets = self._targets(req)
        matches = [
            item
            for item in profile.certifications
            if any(contains(item.name, target) for target in targets)
        ]
        if not matches:
            if profile.certifications:
                return RequirementEvaluation(
                    MatchStatus.UNVERIFIED,
                    0.5,
                    [
                        Evidence("certification", item.name, item.issuer)
                        for item in profile.certifications[:5]
                    ],
                    (
                        "Certifications are recorded, but no direct terminology match was found. "
                        "Review equivalent or differently named credentials before rejecting."
                    ),
                )
            return RequirementEvaluation(
                MatchStatus.MISSING,
                0.0,
                [],
                "No certification evidence is recorded for this person.",
            )
        item = matches[0]
        linked_documents = [doc for doc in profile.documents if doc.certification_id == item.id]
        if req.evidence_required and not linked_documents:
            return RequirementEvaluation(
                MatchStatus.UNVERIFIED,
                0.7,
                [Evidence("certification", item.name, item.issuer)],
                (
                    "Certification is recorded, but the client requires documentary "
                    "evidence and no linked file is present."
                ),
            )
        if item.expiry_date and item.expiry_date < date.today():
            return RequirementEvaluation(
                MatchStatus.PARTIAL,
                0.4,
                [Evidence("certification", item.name, f"expired {item.expiry_date.isoformat()}")],
                "Certification exists but appears expired.",
            )
        evidence = [Evidence("certification", item.name, item.issuer)]
        evidence.extend(
            Evidence("document", doc.title, doc.original_filename) for doc in linked_documents[:3]
        )
        return RequirementEvaluation(
            MatchStatus.MATCHED,
            1.0,
            evidence,
            "Certification record satisfies the requirement"
            + (" and linked documentary evidence is present." if linked_documents else "."),
        )

    def _experience(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        months = sum(
            months_between(item.start_date, item.end_date or date.today())
            for item in profile.employment
        )
        years = months / 12
        minimum = req.minimum_years or 0.0
        if years >= minimum:
            return RequirementEvaluation(
                MatchStatus.MATCHED,
                1.0,
                [Evidence("employment", f"{years:.1f} years total professional history")],
                "Recorded employment duration satisfies the minimum experience requirement.",
            )
        score = min(0.9, years / minimum) if minimum else 1.0
        return RequirementEvaluation(
            MatchStatus.PARTIAL if years else MatchStatus.MISSING,
            score,
            [Evidence("employment", f"{years:.1f} years total professional history")],
            f"Recorded experience is {years:.1f} years vs {minimum:g} required.",
        )

    def _project_experience(
        self,
        profile: PersonProfile,
        req: RequirementLike,
    ) -> RequirementEvaluation:
        targets = self._targets(req)
        matches = [
            item
            for item in profile.projects
            if not targets
            or any(
                contains(item.project_name, target)
                or contains(item.description, target)
                or contains(item.sector, target)
                or contains(item.skills_summary, target)
                for target in targets
            )
        ]
        if req.minimum_count and len(matches) < req.minimum_count:
            score = min(0.9, len(matches) / req.minimum_count)
            return RequirementEvaluation(
                MatchStatus.PARTIAL if matches else MatchStatus.MISSING,
                score,
                [Evidence("project", item.project_name, item.sector) for item in matches[:5]],
                f"Found {len(matches)} relevant projects vs {req.minimum_count} required.",
            )
        if req.minimum_years:
            years = (
                sum(
                    months_between(item.start_date, item.end_date or date.today())
                    for item in matches
                )
                / 12
            )
            if years < req.minimum_years:
                score = min(0.9, years / req.minimum_years)
                return RequirementEvaluation(
                    MatchStatus.PARTIAL if matches else MatchStatus.MISSING,
                    score,
                    [Evidence("project", item.project_name, item.sector) for item in matches[:5]],
                    (
                        f"Relevant project duration is {years:.1f} years "
                        f"vs {req.minimum_years:g} required."
                    ),
                )
        if matches:
            return RequirementEvaluation(
                MatchStatus.MATCHED,
                1.0,
                [Evidence("project", item.project_name, item.sector) for item in matches[:5]],
                "Relevant project experience satisfies the requirement.",
            )
        if profile.projects:
            return RequirementEvaluation(
                MatchStatus.UNVERIFIED,
                0.5,
                [
                    Evidence("project", item.project_name, item.sector)
                    for item in profile.projects[:5]
                ],
                (
                    "Project history exists, but no direct terminology match was found. "
                    "Review the recorded projects for equivalent experience."
                ),
            )
        return RequirementEvaluation(
            MatchStatus.MISSING,
            0.0,
            [],
            "No project evidence is recorded for this person.",
        )

    def _sector(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        targets = self._targets(req)
        employment = [
            item
            for item in profile.employment
            if any(contains(item.industry, target) for target in targets)
        ]
        projects = [
            item
            for item in profile.projects
            if any(contains(item.sector, target) for target in targets)
        ]
        evidence = [
            Evidence("employment", item.employer_name, item.industry) for item in employment[:3]
        ] + [Evidence("project", item.project_name, item.sector) for item in projects[:5]]
        if evidence:
            return RequirementEvaluation(
                MatchStatus.MATCHED,
                1.0,
                evidence,
                "Sector evidence was found.",
            )
        if profile.employment or profile.projects:
            return RequirementEvaluation(
                MatchStatus.UNVERIFIED,
                0.5,
                [],
                (
                    "Professional history exists, but the sector wording is not a direct match. "
                    "This requires verification rather than automatic rejection."
                ),
            )
        return RequirementEvaluation(
            MatchStatus.MISSING,
            0.0,
            [],
            "No sector evidence is recorded for this person.",
        )

    def _geography(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        targets = self._targets(req)
        evidence: list[Evidence] = []
        if any(
            contains(profile.person.country_of_residence, target)
            or contains(profile.person.nationality, target)
            for target in targets
        ):
            evidence.append(
                Evidence(
                    "person",
                    profile.person.display_name,
                    profile.person.country_of_residence,
                )
            )
        evidence.extend(
            Evidence("employment", item.employer_name, item.country)
            for item in profile.employment
            if any(contains(item.country, t) or contains(item.location, t) for t in targets)
        )
        evidence.extend(
            Evidence("project", item.project_name, item.country)
            for item in profile.projects
            if any(contains(item.country, t) or contains(item.location, t) for t in targets)
        )
        if evidence:
            return RequirementEvaluation(
                MatchStatus.MATCHED,
                1.0,
                evidence[:6],
                "Geographic experience was found.",
            )
        return RequirementEvaluation(MatchStatus.MISSING, 0.0, [], "No geographic evidence found.")

    def _client(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        targets = self._targets(req)
        projects = [
            item
            for item in profile.projects
            if any(contains(item.client_name, target) for target in targets)
        ]
        if projects:
            return RequirementEvaluation(
                MatchStatus.MATCHED,
                1.0,
                [Evidence("project", item.project_name, item.client_name) for item in projects[:5]],
                "Client experience was found in project records.",
            )
        if profile.projects:
            return RequirementEvaluation(
                MatchStatus.UNVERIFIED,
                0.5,
                [
                    Evidence("project", item.project_name, item.client_name)
                    for item in profile.projects[:5]
                ],
                (
                    "Project/client history exists, but no direct client-name match was found. "
                    "Review equivalent client categories before rejecting."
                ),
            )
        return RequirementEvaluation(
            MatchStatus.MISSING,
            0.0,
            [],
            "No client/project evidence is recorded for this person.",
        )

    def _availability(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        expected = normalize(req.normalized_value or "available")
        actual = normalize(profile.person.availability_status.value)
        if expected in actual or actual == "available":
            return RequirementEvaluation(
                MatchStatus.MATCHED,
                1.0,
                [
                    Evidence(
                        "person",
                        profile.person.display_name,
                        profile.person.availability_status.value,
                    )
                ],
                "Availability status satisfies the requirement.",
            )
        if actual == "partially available":
            return RequirementEvaluation(
                MatchStatus.PARTIAL,
                0.6,
                [
                    Evidence(
                        "person",
                        profile.person.display_name,
                        profile.person.availability_status.value,
                    )
                ],
                "Person is only partially available.",
            )
        return RequirementEvaluation(
            MatchStatus.MISSING,
            0.0,
            [],
            "Person is not recorded as available.",
        )
