import {
  useQuery
} from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronDown,
  ChevronUp,
  CircleHelp,
  X
} from "lucide-react";
import React from "react";
import {
  Link
} from "react-router-dom";
import { Button } from "../../components/ui";

import {
  api
} from "../../lib/api";
import type {
  CandidateMatch,
  MatchStatus,
  OpportunityRequirement,
  OpportunityRole,
  RequirementMatch
} from "../../types";


import { StatusBadge } from "../../components/StatusBadge";
import { qk } from "../../lib/queryKeys";
import { humanize } from "./shared";
function RequirementStatusIcon({
  status,
}: {
  status: MatchStatus;
}) {
  if (status === "matched") {
    return (
      <Check
        size={15}
        className="text-emerald-600"
      />
    );
  }

  if (status === "partial") {
    return (
      <CircleHelp
        size={15}
        className="text-amber-600"
      />
    );
  }

  if (status === "missing") {
    return (
      <X
        size={15}
        className="text-red-600"
      />
    );
  }

  return (
    <AlertTriangle
      size={15}
      className="text-slate-400"
    />
  );
}

function RequirementResultRow({
  requirement,
  match,
}: {
  requirement:
  | OpportunityRequirement
  | undefined;
  match: RequirementMatch;
}) {
  const [expanded, setExpanded] =
    React.useState(false);

  return (
    <div className="border-t border-slate-100 py-3 first:border-t-0">
      <button
        type="button"
        onClick={() =>
          setExpanded(!expanded)
        }
        className="flex w-full items-start justify-between gap-4 text-left"
      >
        <div className="flex min-w-0 gap-2.5">
          <span className="mt-0.5">
            <RequirementStatusIcon
              status={match.status}
            />
          </span>

          <div className="min-w-0">
            <p className="text-sm font-medium text-ink">
              {requirement?.label ??
                "Requirement"}
            </p>

            <p className="mt-1 text-xs text-slate-400">
              {humanize(
                requirement?.importance ??
                "informational",
              )}{" "}
              · {Math.round(match.score * 100)}%
              satisfied
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <StatusBadge
            value={match.status}
          />
          {expanded ? (
            <ChevronUp size={15} />
          ) : (
            <ChevronDown size={15} />
          )}
        </div>
      </button>

      {expanded && (
        <div className="ml-6 mt-3 rounded-xl bg-slate-50 p-4">
          {match.explanation && (
            <p className="text-sm leading-6 text-slate-600">
              {match.explanation}
            </p>
          )}

          {match.evidence_json &&
            match.evidence_json.length >
            0 && (
              <div className="mt-3">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Evidence
                </p>

                <div className="mt-2 grid gap-2">
                  {match.evidence_json.map(
                    (evidence, index) => (
                      <div
                        key={`${match.id}-${index}`}
                        className="rounded-lg bg-white px-3 py-2 text-xs text-slate-600"
                      >
                        <strong>
                          {String(
                            evidence.label ??
                            evidence.source ??
                            "Evidence",
                          )}
                        </strong>

                        {evidence.detail !=
                          null && (
                            <span className="ml-2 text-slate-400">
                              {String(
                                evidence.detail,
                              )}
                            </span>
                          )}
                      </div>
                    ),
                  )}
                </div>
              </div>
            )}

          {requirement?.source_excerpt && (
            <div className="mt-3 border-l-2 border-slate-300 pl-3 text-xs italic leading-5 text-slate-500">
              Client source: “
              {requirement.source_excerpt}”
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function candidateEvidenceConfidence(candidate: CandidateMatch): number {
  const matches = candidate.requirement_matches;
  if (!matches.length) return 0;

  const evidenceBacked = matches.filter(
    (match) => match.evidence_json && match.evidence_json.length > 0,
  ).length;
  const verified = matches.filter(
    (match) => match.status === "matched",
  ).length;

  return Math.round(
    100 * ((0.6 * evidenceBacked + 0.4 * verified) / matches.length),
  );
}

function CandidateCard({
  candidate,
  role,
}: {
  candidate: CandidateMatch;
  role: OpportunityRole;
}) {
  const [
    expanded,
    setExpanded,
  ] =
    React.useState(
      candidate.rank === 1,
    );

  const requirements =
    new Map(
      role.requirements.map(
        (requirement) => [
          requirement.id,
          requirement,
        ],
      ),
    );
  const evidenceConfidence = candidateEvidenceConfidence(candidate);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5">
      <button
        type="button"
        onClick={() =>
          setExpanded(!expanded)
        }
        className="flex w-full flex-col justify-between gap-4 text-left sm:flex-row sm:items-center"
      >
        <div className="flex items-center gap-4">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-mint font-serif text-evergreen">
            {candidate.rank ??
              "—"}
          </div>

          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold">
                {candidate.person_name ??
                  "Unnamed person"}
              </h4>

              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                Active profile
              </span>

              {candidate.mandatory_failed && (
                <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">
                  Mandatory gap
                </span>
              )}
            </div>

            <p className="mt-1 text-sm text-slate-500">
              {candidate.professional_title ||
                "Professional title not recorded"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-5">
          <div className="text-right">
            <p className="font-serif text-3xl text-evergreen">
              {Math.round(
                candidate.score,
              )}
              %
            </p>
            <p className="text-xs text-slate-400">
              role match
            </p>
          </div>

          {expanded ? (
            <ChevronUp
              className="text-slate-400"
              size={18}
            />
          ) : (
            <ChevronDown
              className="text-slate-400"
              size={18}
            />
          )}
        </div>
      </button>

      {expanded && (
        <div className="mt-5 border-t border-slate-100 pt-5">
          <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-xs text-slate-400">
                Mandatory pass
              </p>
              <p className="mt-1 font-semibold">
                {Math.round(
                  candidate.mandatory_pass_rate *
                  100,
                )}
                %
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-xs text-slate-400">
                Preferred pass
              </p>
              <p className="mt-1 font-semibold">
                {Math.round(
                  candidate.preferred_pass_rate *
                  100,
                )}
                %
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-xs text-slate-400">
                Evidence confidence
              </p>
              <p className="mt-1 font-semibold">
                {evidenceConfidence}%
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-xs text-slate-400">
                Result
              </p>
              <p className="mt-1 font-semibold">
                {candidate.mandatory_failed
                  ? "Has critical gap"
                  : "Compliant"}
              </p>
            </div>
          </div>

          {candidate.explanation && (
            <p className="mb-4 text-sm leading-6 text-slate-600">
              {candidate.explanation}
            </p>
          )}

          <div className="mb-4 rounded-xl border border-emerald-100 bg-emerald-50/60 p-3 text-xs leading-5 text-emerald-800">
            Matching uses active profiles and authoritative structured records only.
            Pending AI suggestions are excluded until they are accepted into the profile.
          </div>

          <div>
            {candidate.requirement_matches.map(
              (match) => (
                <RequirementResultRow
                  key={match.id}
                  match={match}
                  requirement={requirements.get(
                    match.requirement_id,
                  )}
                />
              ),
            )}
          </div>

          <Link
            to={`/people/${candidate.person_id}`}
            className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-evergreen hover:underline"
          >
            Open full person profile
            <ArrowRight size={15} />
          </Link>
        </div>
      )}
    </article>
  );
}

export function RoleWorkspace({
  opportunityId,
  role,
}: {
  opportunityId: string;
  role: OpportunityRole;
}) {
  const [visibleCount, setVisibleCount] = React.useState(10);
  const query = useQuery({
    queryKey: qk("role-matches", opportunityId, role.id),
    queryFn: () =>
      api<CandidateMatch[]>(
        `/opportunities/${opportunityId}/roles/${role.id}/matches`,
      ),
  });

  return (
    <section className="cf-panel">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-serif text-2xl">
              {role.title}
            </h3>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
              {role.quantity} required
            </span>
            {role.is_mandatory && (
              <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">
                Mandatory role
              </span>
            )}
          </div>

          {role.description && (
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              {role.description}
            </p>
          )}
        </div>

        <div className="text-right">
          <p className="text-xs uppercase tracking-wider text-slate-400">
            Requirements
          </p>
          <p className="mt-1 font-serif text-2xl">
            {role.requirements.length}
          </p>
        </div>
      </div>

      <details className="mt-5 border border-slate-100 rounded-xl p-4">
        <summary className="text-xs font-medium cursor-pointer">
          View {role.requirements.length} source requirements
        </summary>
        <div className="divide-y divide-slate-100 mt-3">
          {role.requirements.map((requirement) => <div key={requirement.id} className="py-4">
            <div className="flex flex-wrap items-center gap-2"><StatusBadge value={requirement.importance} />
              <span className="text-xs text-slate-400">{humanize(requirement.requirement_type)}</span></div>
            <p className="font-medium text-sm mt-2">{requirement.label}</p>
            {requirement.source_excerpt && <blockquote className="text-xs text-slate-500 leading-6 border-l-2 border-slate-200 pl-3 mt-2">{requirement.source_excerpt}</blockquote>}
            {requirement.notes && <p className="text-xs text-slate-400 mt-2">{requirement.notes}</p>}
          </div>)}
        </div>
      </details>

      <div className="mt-7">
        <div className="mb-3 flex items-center justify-between">
          <h4 className="font-semibold">
            Ranked candidates
          </h4>
          <span className="text-xs text-slate-400">
            {query.data?.length ?? 0} evaluated
          </span>
        </div>

        {query.isLoading ? (
          <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
            Loading candidate matches…
          </p>
        ) : query.error ? (
          <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
            {query.error.message}
          </p>
        ) : query.data?.length ? (
          <div className="grid gap-3">
            {query.data.slice(0, visibleCount).map(
              (candidate) => (
                <CandidateCard
                  key={candidate.id}
                  candidate={
                    candidate
                  }
                  role={role}
                />
              ),
            )}
            {query.data.length > visibleCount && <Button secondary
              onClick={() => setVisibleCount((count) => count + 10)}>
              Show more candidates ({query.data.length - visibleCount} remaining)
            </Button>}
          </div>
        ) : (
          <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
            No internal candidates were returned
            for this role.
          </p>
        )}
      </div>
    </section>
  );
}
