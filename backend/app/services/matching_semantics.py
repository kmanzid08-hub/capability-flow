from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

from app.core.partial_dates import partial_date_representative

_GENERIC_ROLE_WORDS = {
    "senior",
    "junior",
    "specialist",
    "expert",
    "consultant",
    "professional",
    "officer",
}

_STOPWORDS = {
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

# Deliberately narrow equivalence groups. The groups are used only when two phrases are
# genuine domain synonyms; broad parent disciplines (for example plain "economics") are
# intentionally excluded from more specific groups such as agricultural economics.
_CONCEPT_GROUPS: tuple[tuple[str, ...], ...] = (
    (
        "agricultural economics",
        "agriculture economics",
        "agricultural economist",
        "agribusiness economics",
        "farm economics",
        "rural economics",
    ),
    (
        "impact evaluation",
        "impact evaluations",
        "impact assessment",
        "impact assessments",
        "program evaluation",
        "programme evaluation",
        "evaluation study",
        "evaluation studies",
    ),
    (
        "socio economic",
        "socioeconomic",
        "social economic",
        "household livelihood assessment",
        "livelihood assessment",
        "poverty assessment",
    ),
    (
        "animal science",
        "animal production",
        "livestock production",
        "livestock science",
    ),
    (
        "dairy production",
        "dairy farming",
        "dairy management",
        "dairy cattle",
        "milk production",
    ),
    (
        "statistics",
        "statistical analysis",
        "applied statistics",
        "biostatistics",
    ),
    (
        "data analysis",
        "data analytics",
        "quantitative analysis",
    ),
    (
        "survey sampling",
        "sample design",
        "sampling design",
    ),
    (
        "economic analysis",
        "economic analyses",
        "econometric analysis",
        "econometric analyses",
        "economic modelling",
        "economic modeling",
    ),
    (
        "monitoring and evaluation",
        "monitoring & evaluation",
        "m&e",
    ),
)

_LEADERSHIP_TERMS = (
    "team leader",
    "lead consultant",
    "project lead",
    "project leader",
    "programme lead",
    "program lead",
    "manager",
    "managed",
    "managing",
    "coordinator",
    "coordinated",
    "supervisor",
    "supervised",
    "led ",
    "leading",
)


@dataclass(frozen=True)
class TextEvidence:
    source: str
    label: str
    detail: str | None
    texts: tuple[str | None, ...]
    start_date: str | None = None
    end_date: str | None = None


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().replace("-", " ").replace("_", " ").split())


def _token_stem(token: str) -> str:
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
        "sociolog": "sociology",
        "veterinar": "veterinary",
        "livestock": "livestock",
    }
    for prefix, canonical in canonical_prefixes.items():
        if token.startswith(prefix):
            return canonical
    for suffix in ("ies", "ology", "ation", "ment", "ing", "al", "ic", "s"):
        if len(token) > len(suffix) + 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def meaningful_tokens(value: str | None) -> set[str]:
    return {
        _token_stem(token)
        for token in normalize_text(value).split()
        if len(token) > 2 and token not in _STOPWORDS
    }


def _concept_group(value: str) -> int | None:
    normalized = normalize_text(value)
    for index, aliases in enumerate(_CONCEPT_GROUPS):
        if any(normalize_text(alias) == normalized for alias in aliases):
            return index
    return None


def semantic_strength(haystack: str | None, needle: str | None) -> float:
    """Conservative, directional semantic similarity for qualification evidence.

    ``haystack`` is profile evidence and ``needle`` is the requested qualification.
    A generic evidence phrase that is merely contained inside a more specific requirement
    is not treated as equivalent. For example, ``Economics`` does not fully satisfy
    ``Agricultural Economics``.
    """

    h = normalize_text(haystack)
    n = normalize_text(needle)
    if not h or not n:
        return 0.0
    if h == n:
        return 1.0
    if n in h:
        return 0.98

    h_group = _concept_group(h)
    n_group = _concept_group(n)
    if h_group is not None and h_group == n_group:
        return 0.92
    if n_group is not None and any(
        normalize_text(alias) in h for alias in _CONCEPT_GROUPS[n_group]
    ):
        # Profile fields are often full sentences. An explicit known synonym inside a longer
        # evidence sentence should still satisfy the requested concept.
        return 0.92

    h_tokens = meaningful_tokens(h)
    n_tokens = meaningful_tokens(n)
    if not h_tokens or not n_tokens:
        return 0.0

    requested_coverage = len(h_tokens & n_tokens) / len(n_tokens)
    evidence_coverage = len(h_tokens & n_tokens) / len(h_tokens)

    # Evidence that is only a generic subset of a more specific requirement gets partial
    # credit at most. This is the important guard against Economics -> Agricultural Economics.
    if h in n and h != n:
        if requested_coverage >= 0.67:
            return 0.72
        if requested_coverage >= 0.5:
            return 0.62
        return 0.45

    if requested_coverage >= 1.0:
        return 0.95
    if requested_coverage >= 0.75 and evidence_coverage >= 0.5:
        return 0.88
    if requested_coverage >= 0.6 and evidence_coverage >= 0.5:
        return 0.78

    # Fuzzy matching is only a spelling/reordering fallback when phrases have similar
    # information density. It must not turn a one-word generic field into a specific domain.
    if abs(len(h_tokens) - len(n_tokens)) <= 1:
        ratio = SequenceMatcher(None, h, n).ratio()
        if ratio >= 0.88:
            return 0.75
    return 0.0


def best_strength(texts: Iterable[str | None], target: str) -> float:
    return max((semantic_strength(text, target) for text in texts), default=0.0)


def has_leadership_signal(texts: Iterable[str | None]) -> bool:
    normalized = " ".join(normalize_text(text) for text in texts if text)
    return any(term in normalized for term in _LEADERSHIP_TERMS)


def requirement_needs_leadership(label: str | None) -> bool:
    normalized = normalize_text(label)
    return any(
        marker in normalized
        for marker in ("leading ", "led ", "team leader", "lead consultant", "managing ")
    )


def unique_duration_months(
    intervals: Iterable[tuple[str | None, str | None]],
    *,
    as_of: date | None = None,
) -> int:
    """Return approximate duration without double-counting overlapping records."""

    end_fallback = (as_of or date.today()).isoformat()
    normalized: list[tuple[int, int]] = []
    for start_value, end_value in intervals:
        if not start_value:
            continue
        try:
            start = partial_date_representative(start_value)
            end = partial_date_representative(end_value or end_fallback)
        except Exception:
            continue
        start_index = start.year * 12 + start.month
        end_index = end.year * 12 + end.month
        if end_index < start_index:
            continue
        normalized.append((start_index, end_index))

    if not normalized:
        return 0
    normalized.sort()
    merged: list[tuple[int, int]] = []
    for start_index, end_index in normalized:
        if not merged or start_index > merged[-1][1]:
            merged.append((start_index, end_index))
            continue
        old_start, old_end = merged[-1]
        merged[-1] = (old_start, max(old_end, end_index))
    return sum(max(0, end_index - start_index) for start_index, end_index in merged)


def role_relevance(
    role_title: str,
    *,
    professional_title: str | None,
    summary: str | None,
    employment_titles: Iterable[str],
    project_roles: Iterable[str],
    education_fields: Iterable[str] = (),
    skill_names: Iterable[str] = (),
) -> float:
    """Evidence-backed role relevance used as a bounded scoring component.

    Current and historical role titles remain the strongest signals. Structured education and
    skills provide supporting domain evidence for people whose visible title is generic (for
    example, a lecturer with a Statistics degree), but they cannot on their own create a strong
    leadership signal.
    """

    raw_segments = [
        segment.strip() for segment in re.split(r"/|\bor\b", role_title) if segment.strip()
    ]
    if not raw_segments:
        return 0.0

    title_texts = [professional_title, *employment_titles, *project_roles]
    supporting_texts = [summary, *education_fields, *skill_names]
    segment_scores: list[tuple[str, float]] = []
    for segment in raw_segments:
        tokens = [
            token for token in normalize_text(segment).split() if token not in _GENERIC_ROLE_WORDS
        ]
        target = " ".join(tokens) or segment
        direct = best_strength(title_texts, target)
        supporting = best_strength(supporting_texts, target)
        segment_scores.append((normalize_text(segment), max(direct, supporting * 0.72)))

    leadership = [
        score
        for segment, score in segment_scores
        if "team leader" in segment or segment.startswith("lead ")
    ]
    domain = [
        score
        for segment, score in segment_scores
        if not ("team leader" in segment or segment.startswith("lead "))
    ]
    if leadership and domain:
        return min(1.0, 0.3 * max(leadership) + 0.7 * max(domain))
    return min(1.0, max(score for _, score in segment_scores))
