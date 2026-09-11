export function StatusBadge({ value, label }: { value: string; label?: string; }) {
  const positive = ["ready", "complete", "won", "matched", "selected", "available", "active", "accepted"].includes(value);
  const negative = ["failed", "lost", "missing", "unavailable", "rejected"].includes(value);
  const warning = ["processing", "analyzing", "matching", "building_team", "queued", "extracting", "ready_for_review", "needs_review", "partial", "unverified", "partially_available"].includes(value);
  const tone = positive ? "positive" : negative ? "negative" : warning ? "warning" : "neutral";
  const text = label ?? value.replaceAll("_", " ");
  return <span className={`cf-badge cf-badge-${tone}`}><span className="cf-badge-dot" aria-hidden="true" />{text}</span>;
}
