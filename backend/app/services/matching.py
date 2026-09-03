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


def _token_stem(token: str) -> str:
    """Small domain-safe stemmer used only for qualification terminology."""
    token = token.strip().lower()
    canonical_prefixes = {
        "agricultur": "agriculture",
        "chem": "chemistry",
        "financ": "finance",
        "econom": "economics",
        "account": "accounting",
        "environment": "environment",
        "statist": "statistics",
        "engineer": "engineering",
        "biolog": "biology",
        "geolog": "geology",
    }
    for prefix, canonical in canonical_prefixes.items():
        if token.startswith(prefix):
            return canonical
    for suffix in ("ies", "ology", "ation", "ment", "ing", "al", "ic", "s"):
        if len(token) > len(suffix) + 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _meaningful_tokens(value: str | None) -> set[str]:
    stopwords = {
        "and",
        "or",
        "the",
        "of",
        "in",
        "for",
        "with",
        "to",
        "a",
        "an",
        "degree",
        "master",
        "masters",
        "bachelor",
        "bachelors",
        "qualification",
        "field",
        "fields",
        "area",
        "areas",
        "relevant",
        "related",
        "equivalent",
        "experience",
        "years",
        "year",
        "minimum",
        "professional",
    }
    return {
        _token_stem(token)
        for token in normalize(value).split()
        if len(token) > 2 and token not in stopwords
    }


def match_strength(haystack: str | None, needle: str | None) -> float:
    """Return a conservative 0..1 terminology match strength.

    Exact containment is strongest. Token/stem overlap catches genuine variants such as
    ``agriculture``/``agricultural`` or reordered phrases without treating unrelated
    qualifications at the same degree level as relevant.
    """
    h = normalize(haystack)
    n = normalize(needle)
    if not h or not n:
        return 0.0
    if h == n:
        return 1.0
    if n in h or h in n:
        return 0.98

    h_tokens = _meaningful_tokens(h)
    n_tokens = _meaningful_tokens(n)
    if not h_tokens or not n_tokens:
        return 0.0

    overlap = len(h_tokens & n_tokens) / len(n_tokens)
    if overlap >= 1.0:
        return 0.95
    if overlap >= 0.67:
        return 0.88
    if overlap >= 0.5 and len(n_tokens) >= 2:
        return 0.78

    ratio = SequenceMatcher(None, h, n).ratio()
    return 0.75 if ratio >= 0.86 else 0.0


def contains(haystack: str | None, needle: str | None) -> bool:
    return match_strength(haystack, needle) >= 0.75


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
        mandatory_credit = 0.0
        preferred_total = 0
        preferred_credit = 0.0
        mandatory_failed = False
        mandatory_unverified = False

        for req in requirements:
            result = results[req.id]
            if req.importance == RequirementImportance.INFORMATIONAL:
                continue

            # Preserve source weighting while ensuring mandatory requirements remain dominant.
            importance_multiplier = (
                1.35 if req.importance == RequirementImportance.MANDATORY else 1.0
            )
            weight = max(req.weight, 0.01) * importance_multiplier
            weighted_total += weight
            weighted_score += weight * result.score

            if req.importance == RequirementImportance.MANDATORY:
                mandatory_total += 1
                if result.status == MatchStatus.MATCHED:
                    mandatory_credit += 1.0
                elif result.status == MatchStatus.PARTIAL:
                    # Partial credit improves ranking between genuinely close candidates, but a
                    # partial mandatory item never becomes a full pass merely because its score
                    # happens to be high.
                    mandatory_credit += min(result.score, 0.85)
                    mandatory_failed = True
                elif result.status == MatchStatus.UNVERIFIED:
                    mandatory_credit += min(result.score, 0.7)
                    mandatory_unverified = True
                else:
                    mandatory_failed = True
            elif req.importance == RequirementImportance.PREFERRED:
                preferred_total += 1
                preferred_credit += result.score

        base_score = 100.0 * (weighted_score / weighted_total) if weighted_total else 0.0
        mandatory_rate = mandatory_credit / mandatory_total if mandatory_total else 1.0
        preferred_rate = preferred_credit / preferred_total if preferred_total else 1.0

        # Make the displayed percentage meaningful: strong evidence across all requirements
        # raises it, while confirmed mandatory gaps reduce it proportionally rather than using
        # an arbitrary fixed 79% ceiling. This still lets genuinely close candidates rank well.
        if mandatory_total:
            qualification_factor = 0.55 + (0.45 * mandatory_rate)
            raw_score = base_score * qualification_factor if mandatory_failed else base_score
        else:
            raw_score = base_score

        return CandidateEvaluation(
            person=profile.person,
            score=round(max(0.0, min(raw_score, 100.0)), 2),
            mandatory_pass_rate=round(mandatory_rate, 4),
            preferred_pass_rate=round(preferred_rate, 4),
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

        level_eligible = [
            item
            for item in profile.education
            if DEGREE_RANK.get(item.degree_level.value, 0) >= min_rank
        ]
        if not level_eligible:
            return RequirementEvaluation(
                MatchStatus.MISSING,
                0.0,
                [],
                "No education record meets the required degree level.",
            )

        if not targets:
            field_matches = [(item, 1.0) for item in level_eligible]
        else:
            field_matches = []
            for item in level_eligible:
                strength = max(
                    (
                        max(
                            match_strength(item.field_of_study, target),
                            match_strength(item.degree_name, target),
                        )
                        for target in targets
                    ),
                    default=0.0,
                )
                if strength >= 0.75:
                    field_matches.append((item, strength))

        if field_matches:
            item, strength = max(
                field_matches,
                key=lambda pair: (
                    pair[1],
                    DEGREE_RANK.get(pair[0].degree_level.value, 0),
                ),
            )
            linked_documents = [doc for doc in profile.documents if doc.education_id == item.id]
            evidence = [
                Evidence(
                    "education",
                    item.degree_name or item.degree_level.value,
                    item.field_of_study or item.institution,
                )
            ]
            evidence.extend(
                Evidence("document", doc.title, doc.original_filename)
                for doc in linked_documents[:3]
            )
            if req.evidence_required and not linked_documents:
                return RequirementEvaluation(
                    MatchStatus.UNVERIFIED,
                    min(0.78, strength),
                    evidence,
                    (
                        "Degree level and field match, but required documentary evidence "
                        + "is not linked."
                    ),
                )
            if strength >= 0.88:
                return RequirementEvaluation(
                    MatchStatus.MATCHED,
                    min(1.0, 0.92 + (strength - 0.88)),
                    evidence,
                    "Education level and discipline closely satisfy the requirement.",
                )
            return RequirementEvaluation(
                MatchStatus.PARTIAL,
                strength,
                evidence,
                (
                    "Education is substantively related, but the discipline wording "
                    + "is not an exact match."
                ),
            )

        item = max(level_eligible, key=lambda degree: DEGREE_RANK.get(degree.degree_level.value, 0))
        evidence = [
            Evidence(
                "education",
                item.degree_name or item.degree_level.value,
                item.field_of_study,
            )
        ]
        # Same degree level alone is not a qualification match. Keep the person visible for
        # review, but give only small credit so unrelated master's degrees cannot rank highly.
        return RequirementEvaluation(
            MatchStatus.MISSING
            if req.importance == RequirementImportance.MANDATORY
            else MatchStatus.UNVERIFIED,
            0.15 if req.importance == RequirementImportance.MANDATORY else 0.3,
            evidence,
            (
                "Required degree level is present, but the requested discipline is "
                + "not supported by the education record."
            ),
        )

    def _certification(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        targets = self._targets(req)
        scored = [
            (item, max((match_strength(item.name, target) for target in targets), default=0.0))
            for item in profile.certifications
        ]
        matches = [(item, strength) for item, strength in scored if strength >= 0.75]
        if not matches:
            if profile.certifications:
                return RequirementEvaluation(
                    MatchStatus.MISSING
                    if req.importance == RequirementImportance.MANDATORY
                    else MatchStatus.UNVERIFIED,
                    0.15 if req.importance == RequirementImportance.MANDATORY else 0.3,
                    [
                        Evidence("certification", item.name, item.issuer)
                        for item in profile.certifications[:5]
                    ],
                    "Certification records exist, but none supports the requested credential.",
                )
            return RequirementEvaluation(
                MatchStatus.MISSING,
                0.0,
                [],
                "No certification evidence is recorded for this person.",
            )
        item, strength = max(matches, key=lambda pair: pair[1])
        linked_documents = [doc for doc in profile.documents if doc.certification_id == item.id]
        if req.evidence_required and not linked_documents:
            return RequirementEvaluation(
                MatchStatus.UNVERIFIED,
                min(0.78, strength),
                [Evidence("certification", item.name, item.issuer)],
                "Certification matches, but required documentary evidence is not linked.",
            )
        if item.expiry_date and item.expiry_date < date.today():
            return RequirementEvaluation(
                MatchStatus.PARTIAL,
                0.4,
                [Evidence("certification", item.name, f"expired {item.expiry_date.isoformat()}")],
                "Certification matches but appears expired.",
            )
        evidence = [Evidence("certification", item.name, item.issuer)]
        evidence.extend(
            Evidence("document", doc.title, doc.original_filename) for doc in linked_documents[:3]
        )
        return RequirementEvaluation(
            MatchStatus.MATCHED if strength >= 0.88 else MatchStatus.PARTIAL,
            min(1.0, strength + 0.05),
            evidence,
            "Certification evidence closely matches the requested credential.",
        )

    def _experience(self, profile: PersonProfile, req: RequirementLike) -> RequirementEvaluation:
        targets = self._targets(req)

        def employment_strength(item: EmploymentExperience) -> float:
            if not targets:
                return 1.0
            texts = [
                item.job_title,
                item.industry,
                item.description,
                item.responsibilities,
                item.achievements,
                item.employer_name,
            ]
            return max(
                (match_strength(text, target) for text in texts for target in targets),
                default=0.0,
            )

        relevant = [
            (item, employment_strength(item))
            for item in profile.employment
            if employment_strength(item) >= 0.75
        ]
        months = sum(
            months_between(item.start_date, item.end_date or date.today()) for item, _ in relevant
        )
        years = months / 12
        minimum = req.minimum_years or 0.0

        if relevant and (not minimum or years >= minimum):
            strength = max(score for _, score in relevant)
            return RequirementEvaluation(
                MatchStatus.MATCHED if strength >= 0.88 else MatchStatus.PARTIAL,
                min(1.0, strength + 0.05),
                [
                    Evidence("employment", item.job_title, item.employer_name)
                    for item, _ in relevant[:5]
                ],
                f"Found {years:.1f} years of experience relevant to the requested area.",
            )

        if relevant and minimum:
            score = min(0.85, years / minimum) if minimum else 1.0
            return RequirementEvaluation(
                MatchStatus.PARTIAL,
                score,
                [
                    Evidence("employment", item.job_title, item.employer_name)
                    for item, _ in relevant[:5]
                ],
                f"Relevant experience is {years:.1f} years vs {minimum:g} required.",
            )

        if profile.employment and targets:
            return RequirementEvaluation(
                MatchStatus.MISSING
                if req.importance == RequirementImportance.MANDATORY
                else MatchStatus.UNVERIFIED,
                0.1 if req.importance == RequirementImportance.MANDATORY else 0.3,
                [],
                (
                    "Professional history exists, but it does not evidence the "
                    + "requested experience area."
                ),
            )

        total_months = sum(
            months_between(item.start_date, item.end_date or date.today())
            for item in profile.employment
        )
        total_years = total_months / 12
        if not targets and (not minimum or total_years >= minimum):
            return RequirementEvaluation(
                MatchStatus.MATCHED,
                1.0,
                [Evidence("employment", f"{total_years:.1f} years total professional history")],
                "Recorded professional history satisfies the general experience requirement.",
            )
        return RequirementEvaluation(
            MatchStatus.MISSING,
            0.0,
            [],
            "No qualifying experience evidence was found.",
        )

    def _project_experience(
        self,
        profile: PersonProfile,
        req: RequirementLike,
    ) -> RequirementEvaluation:
        targets = self._targets(req)

        def project_strength(item: ProjectExperience) -> float:
            if not targets:
                return 1.0
            texts = [
                item.project_name,
                item.description,
                item.sector,
                item.skills_summary,
                item.responsibilities,
                item.outcomes,
                item.client_name,
            ]
            return max(
                (match_strength(text, target) for text in texts for target in targets),
                default=0.0,
            )

        scored = [(item, project_strength(item)) for item in profile.projects]
        matches = [(item, strength) for item, strength in scored if strength >= 0.75]

        if req.minimum_count and len(matches) < req.minimum_count:
            score = min(0.85, len(matches) / req.minimum_count)
            return RequirementEvaluation(
                MatchStatus.PARTIAL if matches else MatchStatus.MISSING,
                score,
                [Evidence("project", item.project_name, item.sector) for item, _ in matches[:5]],
                f"Found {len(matches)} relevant projects vs {req.minimum_count} required.",
            )

        if req.minimum_years:
            years = (
                sum(
                    months_between(item.start_date, item.end_date or date.today())
                    for item, _ in matches
                )
                / 12
            )
            if years < req.minimum_years:
                score = min(0.85, years / req.minimum_years)
                return RequirementEvaluation(
                    MatchStatus.PARTIAL if matches else MatchStatus.MISSING,
                    score,
                    [
                        Evidence("project", item.project_name, item.sector)
                        for item, _ in matches[:5]
                    ],
                    (
                        f"Relevant project duration is {years:.1f} years vs "
                        + f"{req.minimum_years:g} required."
                    ),
                )

        if matches:
            strength = max(score for _, score in matches)
            return RequirementEvaluation(
                MatchStatus.MATCHED if strength >= 0.88 else MatchStatus.PARTIAL,
                min(1.0, strength + 0.05),
                [Evidence("project", item.project_name, item.sector) for item, _ in matches[:5]],
                "Relevant project evidence closely satisfies the requirement.",
            )

        if profile.projects:
            return RequirementEvaluation(
                MatchStatus.MISSING
                if req.importance == RequirementImportance.MANDATORY
                else MatchStatus.UNVERIFIED,
                0.1 if req.importance == RequirementImportance.MANDATORY else 0.3,
                [
                    Evidence("project", item.project_name, item.sector)
                    for item in profile.projects[:3]
                ],
                "Project history exists, but none supports the requested project domain.",
            )
        return RequirementEvaluation(
            MatchStatus.MISSING, 0.0, [], "No project evidence is recorded for this person."
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
