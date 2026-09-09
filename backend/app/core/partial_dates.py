import re
from calendar import monthrange
from datetime import date, datetime


class PartialDateError(ValueError):
    pass


def normalize_partial_date(value: object) -> str | None:
    """Normalize an unambiguous date without inventing missing precision."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise PartialDateError("Date must be text, a date, or null")

    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None

    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:[T ].*)", cleaned)
    if match:
        cleaned = match.group(1)

    match = re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", cleaned)
    if match:
        year, month, day = (int(part) for part in match.groups())
        return date(year, month, day).isoformat()

    match = re.fullmatch(r"(\d{4})[/-](\d{1,2})", cleaned)
    if match:
        year, month = (int(part) for part in match.groups())
        _validate_year_month(year, month)
        return f"{year:04d}-{month:02d}"

    match = re.fullmatch(r"(\d{1,2})/(\d{4})", cleaned)
    if match:
        month, year = (int(part) for part in match.groups())
        _validate_year_month(year, month)
        return f"{year:04d}-{month:02d}"

    match = re.fullmatch(r"(\d{4})", cleaned)
    if match:
        year = int(match.group(1))
        date(year, 1, 1)
        return f"{year:04d}"

    match = re.fullmatch(r"(\d{4})-(\d{2})", cleaned)
    if match:
        year, month = (int(part) for part in match.groups())
        _validate_year_month(year, month)
        return cleaned

    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", cleaned)
    if match:
        year, month, day = (int(part) for part in match.groups())
        return date(year, month, day).isoformat()

    for fmt in ("%b %Y", "%B %Y"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
        return f"{parsed.year:04d}-{parsed.month:02d}"

    for fmt in ("%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
        return parsed.date().isoformat()

    raise PartialDateError(
        "Date must be an unambiguous year (YYYY), month (YYYY-MM), or full date (YYYY-MM-DD)"
    )


def _validate_year_month(year: int, month: int) -> None:
    date(year, month, 1)


def partial_date_bounds(value: str) -> tuple[date, date]:
    normalized = normalize_partial_date(value)
    if normalized is None:
        raise PartialDateError("Date is required")

    if len(normalized) == 4:
        year = int(normalized)
        return date(year, 1, 1), date(year, 12, 31)
    if len(normalized) == 7:
        year, month = (int(part) for part in normalized.split("-"))
        last_day = monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    exact = date.fromisoformat(normalized)
    return exact, exact


def partial_date_representative(value: str) -> date:
    """Return a neutral point used only for approximate duration calculations."""
    normalized = normalize_partial_date(value)
    if normalized is None:
        raise PartialDateError("Date is required")

    if len(normalized) == 4:
        return date(int(normalized), 7, 1)
    if len(normalized) == 7:
        year, month = (int(part) for part in normalized.split("-"))
        return date(year, month, min(15, monthrange(year, month)[1]))
    return date.fromisoformat(normalized)


def validate_partial_date_range(
    start_date: str,
    end_date: str | None,
    *,
    start_label: str = "start date",
    end_label: str = "End date",
) -> None:
    if end_date is None:
        return

    start_min, _ = partial_date_bounds(start_date)
    _, end_max = partial_date_bounds(end_date)
    if end_max < start_min:
        raise PartialDateError(f"{end_label} cannot be earlier than {start_label}")


def partial_date_is_expired(value: str, *, as_of: date | None = None) -> bool:
    """Treat partial expiry dates as valid through the end of their stated precision."""
    _, valid_through = partial_date_bounds(value)
    return valid_through < (as_of or date.today())


def months_between_partial(start_date: str, end_date: str) -> int:
    start = partial_date_representative(start_date)
    end = partial_date_representative(end_date)
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return max(0, months)
