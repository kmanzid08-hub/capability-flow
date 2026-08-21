import re
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class OpportunityMetadataSuggestion:
    title: str | None = None
    reference_number: str | None = None
    deadline_at: datetime | None = None


_REFERENCE_PATTERNS = [
    re.compile(
        r"(?:reference|ref(?:erence)?\.?|rfp|tender|solicitation)\s*"
        r"(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9._/\-]{3,})",
        re.IGNORECASE,
    ),
]

_DEADLINE_PATTERNS = [
    re.compile(
        r"(?:deadline|closing date|submission date|due date)\s*[:\-]?\s*"
        r"(\d{4}-\d{1,2}-\d{1,2}(?:[ T]\d{1,2}:\d{2})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:deadline|closing date|submission date|due date)\s*[:\-]?\s*"
        r"(\d{1,2}[ /\-](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[ /\-]\d{4})",
        re.IGNORECASE,
    ),
]


def _parse_deadline(value: str) -> datetime | None:
    value = " ".join(value.split())
    formats = (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%d %b %Y",
        "%d %B %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%b/%Y",
        "%d/%B/%Y",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def suggest_metadata(
    text: str,
    *,
    page_title: str | None = None,
    filename: str | None = None,
) -> OpportunityMetadataSuggestion:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = page_title.strip() if page_title and page_title.strip() else None
    if not title:
        for line in lines[:12]:
            if 6 <= len(line) <= 220 and not line.lower().startswith(
                ("deadline", "reference", "ref:", "date:")
            ):
                title = line
                break
    if not title and filename:
        title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()

    reference = None
    for pattern in _REFERENCE_PATTERNS:
        match = pattern.search(text[:20_000])
        if match:
            reference = match.group(1).strip(" .,:;-")
            break

    deadline = None
    for pattern in _DEADLINE_PATTERNS:
        match = pattern.search(text[:40_000])
        if match:
            deadline = _parse_deadline(match.group(1))
            if deadline:
                break

    return OpportunityMetadataSuggestion(
        title=title[:500] if title else None,
        reference_number=reference[:200] if reference else None,
        deadline_at=deadline,
    )
