import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  LoaderCircle,
  Paperclip,
  Pencil,
  RefreshCw,
  Save,
  Send,
  Trophy,
  XCircle
} from "lucide-react";
import React from "react";
import {
  useNavigate,
  useParams
} from "react-router-dom";
import { localDateTimeInput } from "../lib/dates";

import {
  Button,
  Field,
  TextArea
} from "../components/ui";
import {
  OPPORTUNITY_ANALYSIS_TIMEOUT_MS,
  api
} from "../lib/api";
import type {
  Opportunity,
  OpportunityAnalysis,
  OpportunityRole
} from "../types";


import { StatusBadge } from "../components/StatusBadge";
import { EmptyState, ScoreRing } from "../features/opportunities/display";
import type { WorkspaceTab } from "../features/opportunities/shared";
import { formatDate, percent } from "../features/opportunities/shared";
import { qk } from "../lib/queryKeys";
import { useWorkspace } from "../lib/workspace";

import { GapsPanel } from "../features/opportunities/GapsPanel";
import { IntakeForm } from "../features/opportunities/IntakeForm";
import { RecommendedTeams } from "../features/opportunities/RecommendedTeams";
import { RoleWorkspace } from "../features/opportunities/RoleWorkspace";
import { SourcesPanel } from "../features/opportunities/SourcesPanel";
const wrapper = "cf-page";
export function OpportunityPage() {
  const { opportunityId } =
    useParams();
  const queryClient =
    useQueryClient();
  const navigate = useNavigate();
  const { canWrite, canManage } = useWorkspace();

  const [tab, setTab] =
    React.useState<WorkspaceTab>(
      "overview",
    );

  const [selectedRoleId, setSelectedRoleId] = React.useState("");

  const [editingDetails, setEditingDetails] =
    React.useState(false);
  const [detailsForm, setDetailsForm] =
    React.useState({
      title: "",
      client_name: "",
      reference_number: "",
      deadline_at: "",
      source_url: "",
      description: "",
      internal_notes: "",
      outcome_notes: "",
    });

  const opportunityQuery =
    useQuery({
      queryKey: qk("opportunity", opportunityId),
      queryFn: () =>
        api<Opportunity>(
          `/opportunities/${opportunityId}`,
        ),
      enabled:
        Boolean(opportunityId),
      refetchInterval: (query) => query.state.data?.status === "analyzing" ? 5000 : false,
    });

  const shouldLoadAnalysis =
    Boolean(
      opportunityId &&
      opportunityQuery.data &&
      opportunityQuery.data.status !==
      "new",
    );

  const analysisQuery =
    useQuery({
      queryKey: qk("opportunity-analysis", opportunityId),
      queryFn: () =>
        api<OpportunityAnalysis>(
          `/opportunities/${opportunityId}/analysis`,
        ),
      enabled: shouldLoadAnalysis,
      refetchInterval: (query) => query.state.data && ["queued", "fetching", "extracting", "analyzing", "matching", "building_team"].includes(query.state.data.status) ? 5000 : false,
      retry: false,
    });

  const rolesQuery = useQuery({
    queryKey: qk("opportunity-roles", opportunityId),
    queryFn: () =>
      api<OpportunityRole[]>(
        `/opportunities/${opportunityId}/roles`,
      ),
    enabled:
      Boolean(
        opportunityId &&
        ["complete", "needs_review"].includes(
          analysisQuery.data?.status ?? "",
        ),
      ),
  });

  const updateStatus =
    useMutation({
      mutationFn: (
        status:
          | "pursuing"
          | "not_pursuing"
          | "submitted"
          | "won"
          | "lost"
          | "archived",
      ) =>
        api<Opportunity>(
          `/opportunities/${opportunityId}`,
          {
            method: "PATCH",
            body: JSON.stringify({
              status,
              outcome_notes:
                status === "won" || status === "lost"
                  ? detailsForm.outcome_notes || null
                  : undefined,
            }),
          },
        ),
      onSuccess: (opportunity) => {
        queryClient.setQueryData(
          qk("opportunity", opportunityId),
          opportunity,
        );
        queryClient.invalidateQueries({
          queryKey: qk("opportunities"),
        });
      },
    });

  const saveDetails =
    useMutation({
      mutationFn: () =>
        api<Opportunity>(
          `/opportunities/${opportunityId}`,
          {
            method: "PATCH",
            body: JSON.stringify({
              title: detailsForm.title,
              client_name: detailsForm.client_name || null,
              reference_number:
                detailsForm.reference_number || null,
              deadline_at: detailsForm.deadline_at
                ? new Date(
                  detailsForm.deadline_at,
                ).toISOString()
                : null,
              source_url: detailsForm.source_url || null,
              description: detailsForm.description || null,
              internal_notes:
                detailsForm.internal_notes || null,
              outcome_notes:
                detailsForm.outcome_notes || null,
            }),
          },
        ),
      onSuccess: (opportunity) => {
        queryClient.setQueryData(
          qk("opportunity", opportunityId),
          opportunity,
        );
        queryClient.invalidateQueries({
          queryKey: qk("opportunities"),
        });
        setEditingDetails(false);
      },
    });

  const reanalyze =
    useMutation({
      mutationFn: () =>
        api<OpportunityAnalysis>(
          `/opportunities/${opportunityId}/analyze`,
          {
            method: "POST",
            timeoutMs: OPPORTUNITY_ANALYSIS_TIMEOUT_MS,
          },
        ),

      onSettled: () => {
        queryClient.invalidateQueries({
          queryKey: qk("opportunity", opportunityId),
        });
        queryClient.invalidateQueries({
          queryKey: qk("opportunity-analysis", opportunityId),
        });
        queryClient.invalidateQueries({
          queryKey: qk("opportunity-roles", opportunityId),
        });
        queryClient.invalidateQueries({
          queryKey: qk("opportunity-teams", opportunityId),
        });
        queryClient.invalidateQueries({
          queryKey: qk("opportunity-gaps", opportunityId),
        });
        queryClient.invalidateQueries({ queryKey: qk("opportunities") });
        queryClient.invalidateQueries({ queryKey: qk("role-matches", opportunityId) });
      },
    });

  const opportunity =
    opportunityQuery.data;

  React.useEffect(() => {
    if (!opportunity || editingDetails) {
      return;
    }

    setDetailsForm({
      title: opportunity.title ?? "",
      client_name: opportunity.client_name ?? "",
      reference_number: opportunity.reference_number ?? "",
      deadline_at: localDateTimeInput(opportunity.deadline_at),
      source_url: opportunity.source_url ?? "",
      description: opportunity.description ?? "",
      internal_notes: opportunity.internal_notes ?? "",
      outcome_notes: opportunity.outcome_notes ?? "",
    });
  }, [opportunity, editingDetails]);

  if (opportunityQuery.isLoading) {
    return (
      <div className={wrapper}>
        Loading opportunity…
      </div>
    );
  }

  if (
    opportunityQuery.error ||
    !opportunity ||
    !opportunityId
  ) {
    return (
      <div className={wrapper}>
        <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {opportunityQuery.error?.message ??
            "Opportunity not found"}
        </p>
      </div>
    );
  }

  const analysis =
    analysisQuery.data;
  const roles =
    rolesQuery.data ?? [];

  const activeRole = roles.find((role) => role.id === selectedRoleId) ?? roles[0];

  const tabs: {
    id: WorkspaceTab;
    label: string;
    count?: number;
  }[] = [
      {
        id: "overview",
        label: "Overview",
      },
      {
        id: "roles",
        label: "Roles & matches",
        count: roles.length,
      },
      {
        id: "teams",
        label: "Recommended teams",
      },
      {
        id: "gaps",
        label: "Capability gaps",
      },
      {
        id: "sources",
        label: "Sources",
      },
    ];

  return (
    <div className={wrapper}>
      <button
        type="button"
        onClick={() =>
          navigate(
            "/opportunities",
          )
        }
        className="mb-5 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-ink"
      >
        <ArrowLeft size={16} />
        Opportunities
      </button>

      <section className="cf-opportunity-hero overflow-hidden">
        <div className="p-7 md:p-9">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-start">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge
                  value={
                    opportunity.status
                  }
                />

                {analysis && (
                  <StatusBadge
                    value={
                      analysis.status
                    }
                  />
                )}

                {analysis && (
                  <span className="text-xs text-white/35">
                    Analysis v
                    {analysis.version}
                  </span>
                )}
              </div>

              <h1 className="mt-4 max-w-4xl font-serif text-4xl leading-tight md:text-5xl">
                {opportunity.title}
              </h1>

              <p className="mt-3 text-white/55">
                {opportunity.client_name ||
                  "Client not identified"}
                {opportunity.reference_number
                  ? ` · ${opportunity.reference_number}`
                  : ""}
              </p>

              {analysis?.extracted_summary && (
                <details className="mt-4 max-w-3xl">
                  <summary className="text-xs text-slate-500 cursor-pointer">Analysis summary</summary>
                  <p className="mt-3 text-sm leading-7 text-slate-600">{analysis.extracted_summary}</p>
                </details>
              )}
            </div>

            <div className="grid shrink-0 grid-cols-2 gap-3 lg:w-[320px]">
              <div className="rounded-2xl bg-white/10 p-4">
                <p className="text-xs uppercase tracking-wider text-white/40">
                  Readiness
                </p>
                <p className="mt-2 font-serif text-3xl">
                  {percent(
                    analysis?.readiness_score,
                  )}
                </p>
              </div>

              <div className="rounded-2xl bg-white/10 p-4">
                <p className="text-xs uppercase tracking-wider text-white/40">
                  Deadline
                </p>
                <p className="mt-2 text-sm font-semibold">
                  {formatDate(
                    opportunity.deadline_at,
                  )}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-7 flex flex-wrap gap-2">
            {opportunity.status === "ready" && (
              <>
                <button
                  type="button"
                  disabled={updateStatus.isPending || !canManage}
                  onClick={() =>
                    updateStatus.mutate("pursuing")
                  }
                  className="cf-button cf-button-primary"
                >
                  Pursue opportunity
                </button>

                <button
                  type="button"
                  disabled={updateStatus.isPending || !canManage}
                  onClick={() =>
                    updateStatus.mutate("not_pursuing")
                  }
                  className="cf-button cf-button-secondary"
                >
                  Do not pursue
                </button>
              </>
            )}

            {opportunity.status === "pursuing" && (
              <button
                type="button"
                disabled={
                  !canManage || updateStatus.isPending ||
                  !opportunity.selected_team_id
                }
                onClick={() =>
                  updateStatus.mutate("submitted")
                }
                className="cf-button cf-button-primary"
              >
                <Send size={15} />
                Mark submitted
              </button>
            )}

            {opportunity.status === "submitted" && (
              <>
                <button
                  type="button"
                  disabled={updateStatus.isPending || !canManage}
                  onClick={() =>
                    updateStatus.mutate("won")
                  }
                  className="cf-button cf-button-primary"
                >
                  <Trophy size={15} />
                  Mark won
                </button>

                <button
                  type="button"
                  disabled={updateStatus.isPending || !canManage}
                  onClick={() =>
                    updateStatus.mutate("lost")
                  }
                  className="cf-button cf-button-secondary"
                >
                  <XCircle size={15} />
                  Mark lost
                </button>
              </>
            )}

            <button
              type="button"
              disabled={reanalyze.isPending || !canWrite}
              onClick={() => reanalyze.mutate()}
              className="cf-button cf-button-secondary"
            >
              <RefreshCw
                size={15}
                className={
                  reanalyze.isPending
                    ? "animate-spin"
                    : ""
                }
              />
              Re-analyze
            </button>
          </div>
        </div>

        <nav className="flex overflow-x-auto border-t border-white/10 px-5">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() =>
                setTab(item.id)
              }
              className={`whitespace-nowrap border-b-2 px-4 py-4 text-sm font-semibold transition ${tab === item.id
                ? "border-ink text-ink"
                : "border-transparent text-white/50 hover:text-white"
                }`}
            >
              {item.label}
              {item.count != null && (
                <span className="ml-2 rounded-full bg-white/10 px-2 py-0.5 text-xs">
                  {item.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </section>

      {(reanalyze.error ||
        updateStatus.error ||
        saveDetails.error) && (
          <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">
            {reanalyze.error?.message ??
              updateStatus.error?.message ??
              saveDetails.error?.message}
          </p>
        )}

      <div className="mt-6">
        {tab === "overview" && (
          <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
            <section className="cf-panel">
              <h2 className="font-serif text-2xl">
                Opportunity assessment
              </h2>

              {analysisQuery.isLoading ? (
                <div className="mt-5 flex items-center gap-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-700">
                  <LoaderCircle
                    size={17}
                    className="animate-spin"
                  />
                  Loading analysis…
                </div>
              ) : analysis?.status ===
                "failed" ? (
                <div className="mt-5 rounded-xl bg-red-50 p-4">
                  <p className="font-semibold text-red-800">
                    Analysis failed
                  </p>
                  <p className="mt-2 text-sm text-red-700">
                    {analysis.error_message ||
                      "The requirement could not be analyzed."}
                  </p>
                </div>
              ) : analysis ? (
                <>
                  {analysis.status === "needs_review" && (
                    <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
                      <p className="font-semibold text-amber-900">
                        Requirements need review
                      </p>
                      <p className="mt-2 text-sm leading-6 text-amber-800">
                        {analysis.error_message ||
                          "The source was read, but there is not enough explicit role and qualification information for reliable matching."}
                      </p>
                    </div>
                  )}
                  <div className="mt-6 grid gap-4 sm:grid-cols-3">
                    <ScoreRing
                      score={
                        analysis.readiness_score
                      }
                      label="Company readiness"
                    />

                    <div className="rounded-2xl border border-slate-200 bg-white p-5">
                      <p className="text-xs font-medium tracking-wide text-slate-400">
                        Required roles
                      </p>
                      <p className="mt-4 font-serif text-4xl">
                        {roles.reduce(
                          (
                            total,
                            role,
                          ) =>
                            total +
                            role.quantity,
                          0,
                        )}
                      </p>
                      <p className="mt-2 text-sm text-slate-500">
                        {roles.length} role
                        definitions
                      </p>
                    </div>

                    <div className="rounded-2xl border border-slate-200 bg-white p-5">
                      <p className="text-xs font-medium tracking-wide text-slate-400">
                        Analysis model
                      </p>
                      <p className="mt-4 text-lg font-semibold">
                        {analysis.model_name ||
                          "Not recorded"}
                      </p>
                      <p className="mt-2 text-sm text-slate-500">
                        Completed{" "}
                        {formatDate(
                          analysis.completed_at,
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="mt-7">
                    <h3 className="font-semibold">
                      AI-extracted summary
                    </h3>
                    <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-600">
                      {analysis.extracted_summary ||
                        opportunity.description ||
                        "No summary was returned."}
                    </p>
                  </div>
                </>
              ) : (
                <div className="mt-5 rounded-xl bg-slate-50 p-5">
                  <p className="font-semibold">
                    No analysis yet
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Add a source and run
                    analysis to generate
                    requirements, candidate
                    matches, teams and gaps.
                  </p>
                </div>
              )}
            </section>

            <aside className="space-y-5">
              <div className="cf-panel">
                <h3 className="font-serif text-xl">
                  Opportunity details
                </h3>

                <dl className="mt-5 space-y-4 text-sm">
                  <div>
                    <dt className="text-slate-400">
                      Client
                    </dt>
                    <dd className="mt-1 font-medium">
                      {opportunity.client_name ||
                        "Not identified"}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-400">
                      Reference
                    </dt>
                    <dd className="mt-1 font-medium">
                      {opportunity.reference_number ||
                        "Not identified"}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-400">
                      Deadline
                    </dt>
                    <dd className="mt-1 font-medium">
                      {formatDate(
                        opportunity.deadline_at,
                      )}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-400">
                      Source URL
                    </dt>
                    <dd className="mt-1 break-all font-medium">
                      {opportunity.source_url ? (
                        <a
                          href={
                            opportunity.source_url
                          }
                          target="_blank"
                          rel="noreferrer"
                          className="text-evergreen hover:underline"
                        >
                          Open original source
                        </a>
                      ) : (
                        "Not recorded"
                      )}
                    </dd>
                  </div>
                </dl>
              </div>

              <button
                type="button"
                onClick={() =>
                  setTab("roles")
                }
                className="flex w-full items-center justify-between rounded-2xl bg-evergreen p-5 text-left text-white"
              >
                <span>
                  <span className="block text-xs font-bold uppercase tracking-wider text-mint">
                    Next
                  </span>
                  <span className="mt-1 block font-semibold">
                    Review roles & ranked people
                  </span>
                </span>
                <ArrowRight size={19} />
              </button>
            </aside>
          </div>
        )}

        {tab === "roles" && (
          <>
            {rolesQuery.isLoading ? (
              <p className="rounded-2xl bg-white p-6 text-sm text-slate-500">
                Loading extracted roles…
              </p>
            ) : rolesQuery.error ? (
              <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
                {rolesQuery.error.message}
              </p>
            ) : roles.length ? (
              <div className="grid gap-5">
                <label className="cf-field max-w-xl">
                  <span>Role to review</span>
                  <select className="cf-input" value={activeRole?.id ?? ""}
                    onChange={(event) => setSelectedRoleId(event.target.value)}>
                    {roles.map((role) => <option key={role.id} value={role.id}>
                      {role.title} / {role.quantity} required
                    </option>)}
                  </select>
                </label>
                {activeRole && <RoleWorkspace key={activeRole.id}
                  opportunityId={opportunityId} role={activeRole} />}
              </div>
            ) : (
              <EmptyState
                title="Roles could not be identified reliably"
                text="The source was read, but it did not provide enough explicit staffing information for reliable role matching. Add the TOR, RFP, staffing section, or other detailed requirement and re-analyze."
              />
            )}
          </>
        )}

        {tab === "teams" && (
          <RecommendedTeams
            opportunityId={
              opportunityId
            }
            selectedTeamId={
              opportunity.selected_team_id
            }
            analysisStatus={analysis?.status}
            rolesCount={roles.length}
          />
        )}

        {tab === "gaps" && (
          <GapsPanel
            opportunityId={
              opportunityId
            }
            analysisStatus={analysis?.status}
            rolesCount={roles.length}
          />
        )}

        {tab === "management" && (
          <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
            <section className="cf-panel">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="font-serif text-2xl">
                    Opportunity management
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Maintain authoritative client details,
                    internal notes and outcome information.
                  </p>
                </div>

                {!editingDetails && canWrite && (
                  <button
                    type="button"
                    onClick={() => setEditingDetails(true)}
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold hover:bg-slate-50"
                  >
                    <Pencil size={15} />
                    Edit
                  </button>
                )}
              </div>

              {editingDetails ? (
                <div className="mt-6 grid gap-4">
                  <Field
                    label="Opportunity title"
                    value={detailsForm.title}
                    onChange={(event) =>
                      setDetailsForm((current) => ({
                        ...current,
                        title: event.target.value,
                      }))
                    }
                  />

                  <div className="grid gap-4 md:grid-cols-2">
                    <Field
                      label="Client / organization"
                      value={detailsForm.client_name}
                      onChange={(event) =>
                        setDetailsForm((current) => ({
                          ...current,
                          client_name:
                            event.target.value,
                        }))
                      }
                    />
                    <Field
                      label="Reference number"
                      value={detailsForm.reference_number}
                      onChange={(event) =>
                        setDetailsForm((current) => ({
                          ...current,
                          reference_number:
                            event.target.value,
                        }))
                      }
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <Field
                      label="Deadline"
                      type="datetime-local"
                      value={detailsForm.deadline_at}
                      onChange={(event) =>
                        setDetailsForm((current) => ({
                          ...current,
                          deadline_at:
                            event.target.value,
                        }))
                      }
                    />
                    <Field
                      label="Source URL"
                      type="url"
                      value={detailsForm.source_url}
                      onChange={(event) =>
                        setDetailsForm((current) => ({
                          ...current,
                          source_url:
                            event.target.value,
                        }))
                      }
                    />
                  </div>

                  <TextArea
                    label="Description"
                    rows={5}
                    value={detailsForm.description}
                    onChange={(event) =>
                      setDetailsForm((current) => ({
                        ...current,
                        description:
                          event.target.value,
                      }))
                    }
                  />

                  <TextArea
                    label="Internal notes"
                    rows={5}
                    value={detailsForm.internal_notes}
                    onChange={(event) =>
                      setDetailsForm((current) => ({
                        ...current,
                        internal_notes:
                          event.target.value,
                      }))
                    }
                  />

                  <TextArea
                    label="Outcome notes"
                    rows={4}
                    value={detailsForm.outcome_notes}
                    onChange={(event) =>
                      setDetailsForm((current) => ({
                        ...current,
                        outcome_notes:
                          event.target.value,
                      }))
                    }
                  />

                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      disabled={saveDetails.isPending || !canWrite}
                      onClick={() =>
                        saveDetails.mutate()
                      }
                    >
                      <Save
                        size={15}
                        className="mr-2 inline"
                      />
                      Save details
                    </Button>
                    <Button
                      type="button"
                      secondary
                      disabled={saveDetails.isPending || !canWrite}
                      onClick={() =>
                        setEditingDetails(false)
                      }
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <dl className="mt-6 grid gap-5 text-sm md:grid-cols-2">
                  <div>
                    <dt className="text-slate-400">
                      Client
                    </dt>
                    <dd className="mt-1 font-medium">
                      {opportunity.client_name ||
                        "Not recorded"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">
                      Reference
                    </dt>
                    <dd className="mt-1 font-medium">
                      {opportunity.reference_number ||
                        "Not recorded"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">
                      Decision
                    </dt>
                    <dd className="mt-1 font-medium">
                      {formatDate(
                        opportunity.decision_at,
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">
                      Submitted
                    </dt>
                    <dd className="mt-1 font-medium">
                      {formatDate(
                        opportunity.submitted_at,
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">
                      Outcome
                    </dt>
                    <dd className="mt-1 font-medium">
                      {formatDate(
                        opportunity.outcome_at,
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">
                      Selected team
                    </dt>
                    <dd className="mt-1 font-medium">
                      {opportunity.selected_team_id
                        ? "Team selected"
                        : "No team selected"}
                    </dd>
                  </div>
                  <div className="md:col-span-2">
                    <dt className="text-slate-400">
                      Internal notes
                    </dt>
                    <dd className="mt-2 whitespace-pre-line leading-6 text-slate-600">
                      {opportunity.internal_notes ||
                        "No internal notes"}
                    </dd>
                  </div>
                  <div className="md:col-span-2">
                    <dt className="text-slate-400">
                      Outcome notes
                    </dt>
                    <dd className="mt-2 whitespace-pre-line leading-6 text-slate-600">
                      {opportunity.outcome_notes ||
                        "No outcome notes"}
                    </dd>
                  </div>
                </dl>
              )}
            </section>

            <aside className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <p className="text-xs font-medium tracking-wide text-slate-400">
                  Workflow
                </p>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span>Decision recorded</span>
                    <strong>
                      {opportunity.decision_at
                        ? "Yes"
                        : "No"}
                    </strong>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Team selected</span>
                    <strong>
                      {opportunity.selected_team_id
                        ? "Yes"
                        : "No"}
                    </strong>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Submitted</span>
                    <strong>
                      {opportunity.submitted_at
                        ? "Yes"
                        : "No"}
                    </strong>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Outcome recorded</span>
                    <strong>
                      {opportunity.outcome_at
                        ? "Yes"
                        : "No"}
                    </strong>
                  </div>
                </div>
              </div>

              {opportunity.status === "pursuing" &&
                !opportunity.selected_team_id && (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
                    Select a recommended team before marking
                    the opportunity submitted.
                  </div>
                )}
            </aside>
          </div>
        )}

        {tab === "sources" && (
          <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
            <div className="space-y-6">
              <SourcesPanel opportunityId={opportunityId} />
              <IntakeForm
                compact
                opportunityId={
                  opportunityId
                }
                onComplete={() => {
                  queryClient.invalidateQueries({
                    queryKey: qk("opportunity-roles", opportunityId),
                  });
                  setTab(
                    "overview",
                  );
                }}
              />
            </div>

            <aside className="cf-panel">
              <Paperclip
                size={22}
                className="text-evergreen"
              />
              <h3 className="mt-4 font-serif text-xl">
                Source strategy
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Add the original posting plus
                any detailed TOR, RFP or
                supporting requirement. Every
                re-analysis creates a new
                analysis version instead of
                destroying the previous one.
              </p>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
