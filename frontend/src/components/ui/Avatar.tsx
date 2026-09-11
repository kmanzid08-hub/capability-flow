export function Avatar({ name, large = false }: { name: string; large?: boolean; }) {
  const initials = name.trim().split(/\s+/).filter(Boolean).map((v) => v[0]).filter(Boolean);
  const value = initials.length > 1 ? `${initials[0]}${initials[initials.length - 1]}` : initials[0] ?? "?";
  return <span aria-hidden="true" className={`cf-avatar ${large ? "cf-avatar-large" : ""}`}>{value.toUpperCase()}</span>;
}
