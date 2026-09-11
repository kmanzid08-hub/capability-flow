import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgeCheck
} from "lucide-react";
import {
  Link
} from "react-router-dom";
import { useWorkspace } from "../../lib/workspace";

import {
  Button
} from "../../components/ui";
import {
  api
} from "../../lib/api";
import type {
  Opportunity,
  RecommendedTeam
} from "../../types";


import { StatusBadge } from "../../components/StatusBadge";
import { qk } from "../../lib/queryKeys";
import { EmptyState } from "./display";
export function RecommendedTeams({
  opportunityId,
  selectedTeamId,
  analysisStatus,
  rolesCount,
}: {
  opportunityId: string;
  selectedTeamId: string | null;
  analysisStatus: string | undefined;
  rolesCount: number;
}) {
  const { canManage } = useWorkspace();
  const queryClient = useQueryClient();

  const selectTeam = useMutation({
    mutationFn: (teamId: string) =>
      api<Opportunity>(
        `/opportunities/${opportunityId}/teams/${teamId}/select`,
        { method: "POST" },
      ),
    onSuccess: (opportunity) => {
      queryClient.setQueryData(
        qk("opportunity", opportunityId),
        opportunity,
      );
      queryClient.invalidateQueries({
        queryKey: qk("opportunity-teams", opportunityId),
      });
      queryClient.invalidateQueries({
        queryKey: qk("opportunities"),
      });
    },
  });

  const query = useQuery({
    queryKey: qk("opportunity-teams", opportunityId),
    queryFn: () =>
      api<RecommendedTeam[]>(
        `/opportunities/${opportunityId}/teams`,
      ),
    enabled: analysisStatus === "complete" && rolesCount > 0,
  });

  if (analysisStatus !== "complete" || rolesCount === 0) {
    return (
      <EmptyState
        title="Team recommendation not yet assessable"
        text="Capability Flow needs confirmed role requirements before it can construct and rank an internal team."
      />
    );
  }

  if (query.isLoading) {
    return (
      <p className="rounded-2xl bg-white p-6 text-sm text-slate-500">
        Loading recommended teams…
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
      <EmptyState
        title="No complete team available"
        text="Capability Flow could not construct a full internal team from the current candidate pool. Review the capability gaps for the missing roles."
      />
    );
  }

  return (
    <div className="grid gap-5">
      {query.data.map(
        (team, index) => (
          <article
            key={team.id}
            className={`rounded-3xl border bg-white p-6 ${index === 0
              ? "border-evergreen/30 shadow-soft"
              : "border-slate-200"
              }`}
          >
            <div className="flex flex-col justify-between gap-5 md:flex-row md:items-start">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-serif text-2xl">
                    {team.name}
                  </h3>

                  {index === 0 && (
                    <span className="rounded-full bg-mint px-2.5 py-1 text-xs font-semibold text-evergreen">
                      Best team
                    </span>
                  )}

                  <StatusBadge
                    value={team.status}
                  />
                </div>

                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                  {team.explanation ||
                    "Recommended from the strongest non-conflicting internal assignments."}
                </p>
              </div>

              <div className="text-right">
                <p className="font-serif text-4xl text-evergreen">
                  {Math.round(
                    team.score,
                  )}
                  %
                </p>
                <p className="text-xs text-slate-400">
                  team score
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-2">
              {team.members.map(
                (member) => (
                  <Link
                    key={member.id}
                    to={`/people/${member.person_id}`}
                    className="cf-record hover:border-evergreen/30 hover:bg-slate-50"
                  >
                    <p className="text-xs font-bold uppercase tracking-wider text-evergreen">
                      {member.role_title ??
                        "Assigned role"}
                    </p>
                    <p className="mt-2 font-semibold">
                      {member.person_name ??
                        "Unnamed person"}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {Math.round(
                        member.assignment_score,
                      )}
                      % role match
                    </p>
                  </Link>
                ),
              )}
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button
                type="button"
                secondary={team.id !== selectedTeamId}
                disabled={
                  !canManage || selectTeam.isPending ||
                  team.id === selectedTeamId
                }
                onClick={() => selectTeam.mutate(team.id)}
              >
                {team.id === selectedTeamId
                  ? "Selected team"
                  : "Select this team"}
              </Button>

              {team.id === selectedTeamId && (
                <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
                  <BadgeCheck size={15} />
                  Management selection
                </span>
              )}
            </div>

            {selectTeam.error && (
              <p className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">
                {selectTeam.error.message}
              </p>
            )}

            <div className="mt-5 flex items-center gap-2 text-sm">
              {team.mandatory_constraints_satisfied ? (
                <>
                  <BadgeCheck
                    size={17}
                    className="text-emerald-600"
                  />
                  <span className="font-semibold text-emerald-700">
                    Mandatory team constraints
                    satisfied
                  </span>
                </>
              ) : (
                <>
                  <AlertTriangle
                    size={17}
                    className="text-amber-600"
                  />
                  <span className="font-semibold text-amber-700">
                    Team contains one or more
                    mandatory gaps
                  </span>
                </>
              )}
            </div>
          </article>
        ),
      )}
    </div>
  );
}
