import {
  useQuery
} from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgeCheck
} from "lucide-react";

import {
  api
} from "../../lib/api";
import type {
  CapabilityGap
} from "../../types";


import { StatusBadge } from "../../components/StatusBadge";
import { qk } from "../../lib/queryKeys";
import { EmptyState } from "./display";
export function GapsPanel({
  opportunityId,
  analysisStatus,
  rolesCount,
}: {
  opportunityId: string;
  analysisStatus: string | undefined;
  rolesCount: number;
}) {
  const query = useQuery({
    queryKey: qk("opportunity-gaps", opportunityId),
    queryFn: () =>
      api<CapabilityGap[]>(
        `/opportunities/${opportunityId}/gaps`,
      ),
    enabled: analysisStatus === "complete" && rolesCount > 0,
  });

  if (analysisStatus !== "complete" || rolesCount === 0) {
    return (
      <EmptyState
        title="Capability gaps not yet assessable"
        text="Role and qualification requirements must be identified before Capability Flow can determine whether the firm has a genuine capability gap."
      />
    );
  }

  if (query.isLoading) {
    return (
      <p className="rounded-2xl bg-white p-6 text-sm text-slate-500">
        Loading capability gaps…
      </p>
    );
  }

  if (query.error) {
    return (
      <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
        {query.error.message}
      </p>
    );
  }

  if (!query.data?.length) {
    return (
      <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-8">
        <BadgeCheck
          size={32}
          className="text-emerald-600"
        />
        <h3 className="mt-4 font-serif text-2xl text-emerald-900">
          No critical capability gaps
        </h3>
        <p className="mt-2 text-sm leading-6 text-emerald-800/70">
          The current analysis found fully
          compliant internal candidates for the
          required roles.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {query.data.map(
        (gap) => (
          <article
            key={gap.id}
            className="rounded-2xl border border-red-100 bg-white p-6"
          >
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div className="flex gap-4">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-red-50 text-red-600">
                  <AlertTriangle
                    size={19}
                  />
                </div>

                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold">
                      {gap.label}
                    </h3>
                    <StatusBadge
                      value={
                        gap.severity
                      }
                    />
                  </div>

                  {gap.recommendation && (
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                      {
                        gap.recommendation
                      }
                    </p>
                  )}
                </div>
              </div>

              {gap.best_candidate_score !=
                null && (
                  <div className="shrink-0 text-right">
                    <p className="text-xs uppercase tracking-wider text-slate-400">
                      Best internal option
                    </p>
                    <p className="mt-1 font-serif text-2xl">
                      {Math.round(
                        gap.best_candidate_score,
                      )}
                      %
                    </p>
                  </div>
                )}
            </div>
          </article>
        ),
      )}
    </div>
  );
}
