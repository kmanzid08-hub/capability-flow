import {
    AlertTriangle,
    ArrowRight,
    BriefcaseBusiness,
    CalendarClock,
    CheckCircle2,
    GitBranch,
    Radar,
    Users,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PageHeader } from "../components/ui";
import { api } from "../lib/api";
import type {
    Opportunity,
    PeoplePage,
} from "../types";

const wrapper =
    "mx-auto max-w-7xl px-6 py-10 lg:px-10";

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

function daysUntil(
    value: string | null,
): number | null {
    if (!value) {
        return null;
    }

    const now = new Date();
    const deadline = new Date(value);

    return Math.ceil(
        (deadline.getTime() - now.getTime()) /
        86_400_000,
    );
}

function isActiveOpportunity(
    opportunity: Opportunity,
): boolean {
    return ![
        "won",
        "lost",
        "archived",
        "not_pursuing",
    ].includes(opportunity.status);
}

export function ManagementDashboardPage() {
    const opportunitiesQuery = useQuery({
        queryKey: ["opportunities"],
        queryFn: () =>
            api<Opportunity[]>(
                "/opportunities",
            ),
    });

    const peopleQuery = useQuery({
        queryKey: ["people", "dashboard-count"],
        queryFn: () =>
            api<PeoplePage>(
                "/people?limit=1",
            ),
    });

    const opportunities =
        opportunitiesQuery.data ?? [];

    const active =
        opportunities.filter(
            isActiveOpportunity,
        );

    const pursuing =
        opportunities.filter(
            (item) =>
                item.status === "pursuing",
        );

    const ready =
        opportunities.filter(
            (item) =>
                item.status === "ready",
        );

    const submitted =
        opportunities.filter(
            (item) =>
                item.status === "submitted",
        );

    const won =
        opportunities.filter(
            (item) =>
                item.status === "won",
        );

    const upcoming =
        active
            .filter(
                (item) =>
                    item.deadline_at != null &&
                    (daysUntil(
                        item.deadline_at,
                    ) ?? -1) >= 0,
            )
            .sort((left, right) => {
                const leftDate =
                    left.deadline_at
                        ? new Date(
                            left.deadline_at,
                        ).getTime()
                        : Number.MAX_SAFE_INTEGER;

                const rightDate =
                    right.deadline_at
                        ? new Date(
                            right.deadline_at,
                        ).getTime()
                        : Number.MAX_SAFE_INTEGER;

                return leftDate - rightDate;
            })
            .slice(0, 5);

    const recent =
        [...opportunities]
            .sort(
                (left, right) =>
                    new Date(
                        right.updated_at,
                    ).getTime() -
                    new Date(
                        left.updated_at,
                    ).getTime(),
            )
            .slice(0, 5);

    const cards = [
        {
            label: "Active opportunities",
            value: active.length,
            note: `${opportunities.length} total captured`,
            icon: Radar,
            tone:
                "bg-mint text-evergreen",
        },
        {
            label: "In pursuit",
            value: pursuing.length,
            note: `${ready.length} ready for decision`,
            icon: GitBranch,
            tone:
                "bg-[#fde7df] text-coral",
        },
        {
            label: "Submitted",
            value: submitted.length,
            note: `${won.length} opportunities won`,
            icon: BriefcaseBusiness,
            tone:
                "bg-sand text-ink",
        },
        {
            label: "People available to match",
            value:
                peopleQuery.data?.total ??
                "—",
            note:
                "Capability records in this workspace",
            icon: Users,
            tone:
                "bg-slate-100 text-slate-700",
        },
    ];

    return (
        <div className={wrapper}>
            <PageHeader
                eyebrow="Management"
                title="Capability readiness dashboard"
            >
                See the opportunity pipeline,
                staffing workload, deadlines and
                decisions that need attention.
            </PageHeader>

            {(opportunitiesQuery.error ||
                peopleQuery.error) && (
                    <p className="mb-6 rounded-xl bg-red-50 p-4 text-sm text-red-700">
                        {opportunitiesQuery.error?.message ??
                            peopleQuery.error?.message}
                    </p>
                )}

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {cards.map(
                    (card) => {
                        const Icon = card.icon;

                        return (
                            <article
                                key={card.label}
                                className="rounded-2xl border border-slate-200 bg-white p-5"
                            >
                                <div
                                    className={`grid h-10 w-10 place-items-center rounded-xl ${card.tone}`}
                                >
                                    <Icon size={19} />
                                </div>

                                <p className="mt-5 text-xs font-bold uppercase tracking-[.15em] text-slate-400">
                                    {card.label}
                                </p>

                                <p className="mt-2 font-serif text-4xl">
                                    {card.value}
                                </p>

                                <p className="mt-2 text-sm text-slate-500">
                                    {card.note}
                                </p>
                            </article>
                        );
                    },
                )}
            </section>

            <div className="mt-7 grid gap-6 xl:grid-cols-[1.1fr_.9fr]">
                <section className="rounded-2xl bg-white p-6 shadow-soft">
                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <h2 className="font-serif text-2xl">
                                Upcoming deadlines
                            </h2>
                            <p className="mt-1 text-sm text-slate-500">
                                Active opportunities with the
                                nearest deadlines.
                            </p>
                        </div>

                        <CalendarClock
                            size={22}
                            className="text-evergreen"
                        />
                    </div>

                    {opportunitiesQuery.isLoading ? (
                        <p className="mt-6 text-sm text-slate-500">
                            Loading deadlines…
                        </p>
                    ) : upcoming.length ? (
                        <div className="mt-5 divide-y divide-slate-100">
                            {upcoming.map(
                                (opportunity) => {
                                    const days =
                                        daysUntil(
                                            opportunity.deadline_at,
                                        );

                                    return (
                                        <Link
                                            key={opportunity.id}
                                            to={`/opportunities/${opportunity.id}`}
                                            className="flex items-center justify-between gap-5 py-4 first:pt-0 last:pb-0"
                                        >
                                            <div className="min-w-0">
                                                <p className="truncate font-semibold">
                                                    {opportunity.title}
                                                </p>
                                                <p className="mt-1 text-sm text-slate-500">
                                                    {opportunity.client_name ||
                                                        "Client not identified"}
                                                </p>
                                            </div>

                                            <div className="shrink-0 text-right">
                                                <p
                                                    className={`text-sm font-semibold ${days != null &&
                                                        days <= 7
                                                        ? "text-coral"
                                                        : "text-ink"
                                                        }`}
                                                >
                                                    {formatDate(
                                                        opportunity.deadline_at,
                                                    )}
                                                </p>

                                                <p className="mt-1 text-xs text-slate-400">
                                                    {days === 0
                                                        ? "Due today"
                                                        : days === 1
                                                            ? "1 day left"
                                                            : `${days} days left`}
                                                </p>
                                            </div>
                                        </Link>
                                    );
                                },
                            )}
                        </div>
                    ) : (
                        <div className="mt-6 rounded-xl bg-slate-50 p-5 text-sm text-slate-500">
                            No active opportunity deadlines
                            are currently recorded.
                        </div>
                    )}
                </section>

                <section className="rounded-2xl border border-slate-200 bg-white p-6">
                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <h2 className="font-serif text-2xl">
                                Decision queue
                            </h2>
                            <p className="mt-1 text-sm text-slate-500">
                                Opportunities ready for a
                                pursue / no-pursue decision.
                            </p>
                        </div>

                        <CheckCircle2
                            size={22}
                            className="text-evergreen"
                        />
                    </div>

                    {ready.length ? (
                        <div className="mt-5 grid gap-3">
                            {ready
                                .slice(0, 5)
                                .map(
                                    (opportunity) => (
                                        <Link
                                            key={opportunity.id}
                                            to={`/opportunities/${opportunity.id}`}
                                            className="rounded-xl border border-slate-200 p-4 hover:border-evergreen/30 hover:bg-slate-50"
                                        >
                                            <p className="font-semibold">
                                                {opportunity.title}
                                            </p>
                                            <p className="mt-1 text-sm text-slate-500">
                                                {opportunity.client_name ||
                                                    "Client not identified"}
                                            </p>
                                        </Link>
                                    ),
                                )}
                        </div>
                    ) : (
                        <div className="mt-5 rounded-xl bg-slate-50 p-5">
                            <p className="text-sm font-semibold">
                                Nothing waiting for decision
                            </p>
                            <p className="mt-1 text-sm leading-6 text-slate-500">
                                Analyzed opportunities that reach
                                the ready state will appear here.
                            </p>
                        </div>
                    )}

                    <Link
                        to="/pipeline"
                        className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-evergreen hover:underline"
                    >
                        Open full pipeline
                        <ArrowRight size={15} />
                    </Link>
                </section>
            </div>

            <section className="mt-7 rounded-2xl border border-slate-200 bg-white p-6">
                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                    <div>
                        <h2 className="font-serif text-2xl">
                            Recent opportunity activity
                        </h2>
                        <p className="mt-1 text-sm text-slate-500">
                            The most recently updated
                            opportunity records.
                        </p>
                    </div>

                    <Link
                        to="/opportunities"
                        className="inline-flex items-center gap-2 text-sm font-semibold text-evergreen hover:underline"
                    >
                        All opportunities
                        <ArrowRight size={15} />
                    </Link>
                </div>

                {recent.length ? (
                    <div className="mt-5 overflow-x-auto">
                        <table className="w-full min-w-[720px] text-left text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 text-xs uppercase tracking-wider text-slate-400">
                                    <th className="pb-3 pr-5">
                                        Opportunity
                                    </th>
                                    <th className="pb-3 pr-5">
                                        Status
                                    </th>
                                    <th className="pb-3 pr-5">
                                        Deadline
                                    </th>
                                    <th className="pb-3">
                                        Updated
                                    </th>
                                </tr>
                            </thead>

                            <tbody>
                                {recent.map(
                                    (opportunity) => (
                                        <tr
                                            key={opportunity.id}
                                            className="border-b border-slate-100 last:border-0"
                                        >
                                            <td className="py-4 pr-5">
                                                <Link
                                                    to={`/opportunities/${opportunity.id}`}
                                                    className="font-semibold hover:text-evergreen"
                                                >
                                                    {opportunity.title}
                                                </Link>
                                                <p className="mt-1 text-xs text-slate-400">
                                                    {opportunity.client_name ||
                                                        "Client not identified"}
                                                </p>
                                            </td>

                                            <td className="py-4 pr-5 capitalize">
                                                {opportunity.status.replaceAll(
                                                    "_",
                                                    " ",
                                                )}
                                            </td>

                                            <td className="py-4 pr-5">
                                                {formatDate(
                                                    opportunity.deadline_at,
                                                )}
                                            </td>

                                            <td className="py-4 text-slate-500">
                                                {formatDate(
                                                    opportunity.updated_at,
                                                )}
                                            </td>
                                        </tr>
                                    ),
                                )}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="mt-5 flex items-center gap-3 rounded-xl bg-slate-50 p-5 text-sm text-slate-500">
                        <AlertTriangle
                            size={17}
                            className="text-slate-400"
                        />
                        No opportunities have been captured
                        yet.
                    </div>
                )}
            </section>
        </div>
    );
}