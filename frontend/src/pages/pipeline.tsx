import {
    ArrowRight,
    CalendarDays,
    Check,
    ChevronDown,
    Filter,
    Search,
} from "lucide-react";
import React from "react";
import {
    useMutation,
    useQuery,
    useQueryClient,
} from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PageHeader } from "../components/ui";
import { api } from "../lib/api";
import type {
    Opportunity,
    OpportunityStatus,
} from "../types";

const wrapper =
    "mx-auto max-w-[1500px] px-6 py-10 lg:px-10";

type PipelineColumn = {
    id: string;
    label: string;
    statuses: OpportunityStatus[];
    description: string;
};

const columns: PipelineColumn[] = [
    {
        id: "intake",
        label: "Intake & review",
        statuses: [
            "new",
            "analyzing",
            "needs_review",
        ],
        description:
            "Captured or still being analyzed.",
    },
    {
        id: "ready",
        label: "Ready to decide",
        statuses: ["ready"],
        description:
            "Analysis complete and waiting for management.",
    },
    {
        id: "pursuing",
        label: "Pursuing",
        statuses: ["pursuing"],
        description:
            "Approved opportunities being prepared.",
    },
    {
        id: "submitted",
        label: "Submitted",
        statuses: ["submitted"],
        description:
            "Proposal or application submitted.",
    },
    {
        id: "closed",
        label: "Closed",
        statuses: [
            "won",
            "lost",
            "not_pursuing",
            "archived",
        ],
        description:
            "Completed or intentionally closed.",
    },
];

function formatDate(
    value: string | null,
): string {
    if (!value) {
        return "No deadline";
    }

    return new Date(value).toLocaleDateString(
        undefined,
        {
            day: "numeric",
            month: "short",
            year: "numeric",
        },
    );
}

function statusLabel(
    value: OpportunityStatus,
): string {
    return value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) =>
            letter.toUpperCase(),
        );
}

function statusTone(
    value: OpportunityStatus,
): string {
    if (value === "won") {
        return "bg-emerald-50 text-emerald-700";
    }

    if (
        value === "lost" ||
        value === "not_pursuing"
    ) {
        return "bg-red-50 text-red-700";
    }

    if (
        value === "pursuing" ||
        value === "submitted"
    ) {
        return "bg-mint text-evergreen";
    }

    if (
        value === "ready" ||
        value === "needs_review"
    ) {
        return "bg-amber-50 text-amber-700";
    }

    return "bg-slate-100 text-slate-600";
}

function allowedNextStatuses(
    status: OpportunityStatus,
    hasSelectedTeam: boolean,
): OpportunityStatus[] {
    const map: Record<OpportunityStatus, OpportunityStatus[]> = {
        new: ["needs_review", "ready", "archived"],
        analyzing: ["needs_review", "ready"],
        needs_review: ["ready", "not_pursuing", "archived"],
        ready: ["pursuing", "not_pursuing", "archived"],
        pursuing: hasSelectedTeam
            ? ["ready", "submitted", "not_pursuing", "archived"]
            : ["ready", "not_pursuing", "archived"],
        submitted: ["pursuing", "won", "lost", "archived"],
        won: ["archived"],
        lost: ["pursuing", "archived"],
        not_pursuing: ["ready", "pursuing", "archived"],
        archived: [],
    };

    return map[status];
}

function OpportunityCard({
    opportunity,
}: {
    opportunity: Opportunity;
}) {
    const queryClient =
        useQueryClient();
    const [statusOpen, setStatusOpen] =
        React.useState(false);

    const mutation =
        useMutation({
            mutationFn: (
                status: OpportunityStatus,
            ) =>
                api<Opportunity>(
                    `/opportunities/${opportunity.id}`,
                    {
                        method: "PATCH",
                        body: JSON.stringify({
                            status,
                        }),
                    },
                ),

            onSuccess: () => {
                setStatusOpen(false);

                queryClient.invalidateQueries({
                    queryKey: [
                        "opportunities",
                    ],
                });

                queryClient.invalidateQueries({
                    queryKey: [
                        "opportunity",
                        opportunity.id,
                    ],
                });
            },
        });

    const workflowStatuses =
        allowedNextStatuses(
            opportunity.status,
            Boolean(opportunity.selected_team_id),
        );

    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
                <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusTone(
                        opportunity.status,
                    )}`}
                >
                    {statusLabel(
                        opportunity.status,
                    )}
                </span>

                <div className="relative">
                    <button
                        type="button"
                        disabled={mutation.isPending}
                        onClick={() =>
                            setStatusOpen(
                                !statusOpen,
                            )
                        }
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-500 hover:bg-slate-50 disabled:opacity-50"
                    >
                        Move
                        <ChevronDown size={13} />
                    </button>

                    {statusOpen && (
                        <div className="absolute right-0 top-full z-20 mt-2 w-44 overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl">
                            {workflowStatuses.map(
                                (status) => (
                                    <button
                                        key={status}
                                        type="button"
                                        onClick={() =>
                                            mutation.mutate(
                                                status,
                                            )
                                        }
                                        className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs hover:bg-slate-50"
                                    >
                                        {statusLabel(
                                            status,
                                        )}

                                        {opportunity.status ===
                                            status && (
                                                <Check
                                                    size={13}
                                                    className="text-evergreen"
                                                />
                                            )}
                                    </button>
                                ),
                            )}
                        </div>
                    )}
                </div>
            </div>

            <Link
                to={`/opportunities/${opportunity.id}`}
                className="group mt-4 block"
            >
                <h3 className="font-serif text-xl leading-snug group-hover:text-evergreen">
                    {opportunity.title}
                </h3>

                <p className="mt-2 text-sm text-slate-500">
                    {opportunity.client_name ||
                        "Client not identified"}
                </p>

                {opportunity.selected_team_id && (
                    <p className="mt-2 text-xs font-semibold text-evergreen">
                        Team selected
                    </p>
                )}
            </Link>

            <div className="mt-5 flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                    <CalendarDays size={14} />
                    {formatDate(
                        opportunity.deadline_at,
                    )}
                </div>

                <Link
                    to={`/opportunities/${opportunity.id}`}
                    className="text-evergreen"
                    aria-label={`Open ${opportunity.title}`}
                >
                    <ArrowRight size={17} />
                </Link>
            </div>

            {mutation.error && (
                <p className="mt-3 rounded-lg bg-red-50 p-2 text-xs text-red-700">
                    {mutation.error.message}
                </p>
            )}
        </article>
    );
}

export function PipelinePage() {
    const [search, setSearch] =
        React.useState("");

    const [closedVisible, setClosedVisible] =
        React.useState(false);

    const query = useQuery({
        queryKey: ["opportunities"],
        queryFn: () =>
            api<Opportunity[]>(
                "/opportunities",
            ),
    });

    const filtered =
        (query.data ?? []).filter(
            (opportunity) => {
                const haystack = [
                    opportunity.title,
                    opportunity.client_name,
                    opportunity.reference_number,
                ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();

                return haystack.includes(
                    search.toLowerCase(),
                );
            },
        );

    const visibleColumns =
        closedVisible
            ? columns
            : columns.filter(
                (column) =>
                    column.id !== "closed",
            );

    return (
        <div className={wrapper}>
            <PageHeader
                eyebrow="Management"
                title="Opportunity pipeline"
            >
                Move opportunities from intake to
                decision, pursuit, submission and final
                outcome without losing the capability
                analysis behind each record.
            </PageHeader>

            <div className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                <div className="flex min-w-[280px] max-w-lg flex-1 items-center gap-3 rounded-xl border border-slate-200 bg-white px-4">
                    <Search
                        size={17}
                        className="text-slate-400"
                    />

                    <input
                        value={search}
                        onChange={(event) =>
                            setSearch(
                                event.target.value,
                            )
                        }
                        placeholder="Search title, client or reference…"
                        className="w-full bg-transparent py-3 text-sm outline-none"
                    />
                </div>

                <button
                    type="button"
                    onClick={() =>
                        setClosedVisible(
                            !closedVisible,
                        )
                    }
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold hover:bg-slate-50"
                >
                    <Filter size={16} />
                    {closedVisible
                        ? "Hide closed"
                        : "Show closed"}
                </button>
            </div>

            {query.isLoading ? (
                <div className="rounded-2xl bg-white p-8 text-sm text-slate-500">
                    Loading pipeline…
                </div>
            ) : query.error ? (
                <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
                    {query.error.message}
                </p>
            ) : (
                <div
                    className={`grid items-start gap-4 ${closedVisible
                            ? "xl:grid-cols-5"
                            : "xl:grid-cols-4"
                        }`}
                >
                    {visibleColumns.map(
                        (column) => {
                            const items =
                                filtered.filter(
                                    (opportunity) =>
                                        column.statuses.includes(
                                            opportunity.status,
                                        ),
                                );

                            return (
                                <section
                                    key={column.id}
                                    className="min-w-0 rounded-2xl bg-slate-100/70 p-3"
                                >
                                    <div className="px-2 pb-3 pt-1">
                                        <div className="flex items-center justify-between gap-3">
                                            <h2 className="font-semibold">
                                                {column.label}
                                            </h2>

                                            <span className="grid min-w-6 place-items-center rounded-full bg-white px-2 py-1 text-xs font-semibold text-slate-500">
                                                {items.length}
                                            </span>
                                        </div>

                                        <p className="mt-1 text-xs leading-5 text-slate-400">
                                            {column.description}
                                        </p>
                                    </div>

                                    <div className="grid gap-3">
                                        {items.length ? (
                                            items.map(
                                                (
                                                    opportunity,
                                                ) => (
                                                    <OpportunityCard
                                                        key={
                                                            opportunity.id
                                                        }
                                                        opportunity={
                                                            opportunity
                                                        }
                                                    />
                                                ),
                                            )
                                        ) : (
                                            <div className="rounded-xl border border-dashed border-slate-300 bg-white/60 p-5 text-center text-xs text-slate-400">
                                                No opportunities
                                                in this stage.
                                            </div>
                                        )}
                                    </div>
                                </section>
                            );
                        },
                    )}
                </div>
            )}
        </div>
    );
}