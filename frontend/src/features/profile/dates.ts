export function formatPartialEvidenceDate(value: string): string {
  if (/^\d{4}$/.test(value)) return value;

  if (/^\d{4}-\d{2}$/.test(value)) {
    const [year, month] = value.split("-").map(Number);
    if (month < 1 || month > 12) return value;
    const date = new Date(Date.UTC(year, month - 1, 1));
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        timeZone: "UTC",
      });
    }
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const date = new Date(`${value}T00:00:00Z`);
    if (!Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value) {
      return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      });
    }
  }

  return value;
}

export function formatExperiencePeriod(
  startDate: string,
  endDate: string | null,
  isCurrent: boolean,
): string {
  const start = formatPartialEvidenceDate(startDate);
  const end = isCurrent
    ? "Present"
    : endDate
      ? formatPartialEvidenceDate(endDate)
      : "Not recorded";

  return `${start} – ${end}`;
}
