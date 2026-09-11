import type { Opportunity } from "../../types";
export type IntakeMode =
  | "url"
  | "text"
  | "file";

export type OpportunitySource = {
  id: string;
  opportunity_id: string;
  source_type: string;
  source_url: string | null;
  original_filename: string | null;
  stored_filename: string | null;
  mime_type: string | null;
  file_size: number | null;
  content_hash: string;
  created_at: string;
  updated_at: string;
};

export type OpportunityIntakeResponse = {
  opportunity: Opportunity;
  source: OpportunitySource;
};

export type WorkspaceTab =
  | "overview"
  | "roles"
  | "teams"
  | "gaps"
  | "management"
  | "sources";

export function percent(
  value: number | null | undefined,
): string {
  if (value == null) {
    return "—";
  }

  return `${Math.round(value)}%`;
}

export function humanize(
  value: string,
): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

export function formatDate(
  value: string | null,
): string {
  if (!value) {
    return "Not recorded";
  }

  return new Date(value).toLocaleDateString(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
    },
  );
}

export function statusClasses(
  status: string,
): string {
  if (
    [
      "ready",
      "complete",
      "won",
      "matched",
      "selected",
    ].includes(status)
  ) {
    return "bg-emerald-50 text-emerald-700";
  }

  if (
    [
      "analyzing",
      "matching",
      "building_team",
      "fetching",
      "extracting",
      "queued",
      "pursuing",
      "submitted",
      "partial",
      "recommended",
    ].includes(status)
  ) {
    return "bg-amber-50 text-amber-700";
  }

  if (
    [
      "failed",
      "lost",
      "missing",
      "not_pursuing",
    ].includes(status)
  ) {
    return "bg-red-50 text-red-700";
  }

  return "bg-slate-100 text-slate-600";
}
