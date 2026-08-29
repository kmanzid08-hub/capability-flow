
import {
    AlertTriangle,
    ArrowLeft,
    ArrowRight,
    BadgeCheck,
    Check,
    ChevronDown,
    ChevronUp,
    CircleHelp,
    Download,
    FileText,
    Link2,
    LoaderCircle,
    Paperclip,
    Pencil,
    Radar,
    RefreshCw,
    Save,
    Search,
    Send,
    Sparkles,
    Trash2,
    Trophy,
    X,
    XCircle,
} from "lucide-react";
import React from "react";
import {
    useMutation,
    useQuery,
    useQueryClient,
} from "@tanstack/react-query";
import {
    Link,
    useNavigate,
    useParams,
} from "react-router-dom";

import {
    Button,
    Field,
    PageHeader,
    TextArea,
} from "../components/ui";
import { OPPORTUNITY_ANALYSIS_TIMEOUT_MS, api, apiDownload } from "../lib/api";
import type {
    CandidateMatch,
    CapabilityGap,
    MatchStatus,
    Opportunity,
    OpportunityAnalysis,
    OpportunityRequirement,
    OpportunityRole,
    RecommendedTeam,
    RequirementMatch,
} from "../types";

const wrapper =
    "mx-auto max-w-7xl px-6 py-10 lg:px-10";

type IntakeMode =
    | "url"
    | "text";

type OpportunitySource = {
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

type OpportunityIntakeResponse = {
    opportunity: Opportunity;
    source: OpportunitySource;
};

type WorkspaceTab =
    | "overview"
    | "roles"
    | "teams"
    | "gaps"
    | "management"
    | "sources";

function percent(
    value: number | null | undefined,
): string {
    if (value == null) {
        return "—";
    }

    return `${Math.round(value)}%`;
}

function humanize(
    value: string,
): string {
    return value
        .replace(/_/g, " ")
        .replace(/\b\w/g, (character) =>
            character.toUpperCase(),
        );
}

function formatDate(
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

function statusClasses(
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

function StatusBadge({
    value,
}: {
    value: string;
}) {
    return (
        <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusClasses(
                value,
            )}`}
        >
            {humanize(value)}
        </span>
    );
}

function ScoreRing({
    score,
    label,
}: {
    score: number | null | undefined;
    label: string;
}) {
    const hasScore = score != null;
    const normalized = hasScore
        ? Math.max(0, Math.min(100, score))
        : 0;

    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[.16em] text-slate-400">
                {label}
            </p>

            <div className="mt-4 flex items-end gap-2">
                <strong className="font-serif text-4xl text-evergreen">
                    {hasScore ? Math.round(normalized) : "—"}
                </strong>
                <span className="pb-1 text-sm text-slate-400">
                    / 100
                </span>
            </div>

            <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                    className="h-full rounded-full bg-evergreen transition-all"
                    style={{
                        width: `${normalized}%`,
                    }}
                />
            </div>
        </div>
    );
}

function EmptyState({
    title,
    text,
}: {
    title: string;
    text: string;
}) {
    return (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
            <Radar
                size={34}
                className="mx-auto text-slate-300"
            />
            <h3 className="mt-4 font-serif text-2xl">
                {title}
            </h3>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
                {text}
            </p>
        </div>
    );
}

function IntakeForm({
    compact = false,
    opportunityId,
    onComplete,
}: {
    compact?: boolean;
    opportunityId?: string;
    onComplete?: (
        opportunity: Opportunity,
    ) => void;
}) {
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [mode, setMode] =
        React.useState<IntakeMode>("url");
    const [title, setTitle] =
        React.useState("");
    const [clientName, setClientName] =
        React.useState("");
    const [url, setUrl] =
        React.useState("");
    const [text, setText] =
        React.useState("");

    const mutation = useMutation({
        mutationFn: async () => {
            if (opportunityId) {
                let source: { id: string; status: string };

                if (mode === "url") {
                    if (!url.trim()) {
                        throw new Error("Paste the opportunity URL first.");
                    }
                    source = await api(
                        `/opportunities/${opportunityId}/sources/url`,
                        {
                            method: "POST",
                            body: JSON.stringify({ url: url.trim() }),
                        },
                    );
                } else {
                    if (text.trim().length < 20) {
                        throw new Error(
                            "Paste at least 20 characters of the client requirement.",
                        );
                    }
                    source = await api(
                        `/opportunities/${opportunityId}/sources/text`,
                        {
                            method: "POST",
                            body: JSON.stringify({ text: text.trim() }),
                        },
                    );
                }

                void source;
                await api<OpportunityAnalysis>(
                    `/opportunities/${opportunityId}/analyze`,
                    {
                        method: "POST",
                        timeoutMs: OPPORTUNITY_ANALYSIS_TIMEOUT_MS,
                    },
                );
                return api<Opportunity>(`/opportunities/${opportunityId}`);
            }

            let intake: OpportunityIntakeResponse;
            if (mode === "url") {
                if (!url.trim()) {
                    throw new Error("Paste the opportunity URL first.");
                }
                intake = await api<OpportunityIntakeResponse>(
                    "/opportunities/intake/url",
                    {
                        method: "POST",
                        body: JSON.stringify({
                            url: url.trim(),
                            title: title.trim() || null,
                            client_name: clientName.trim() || null,
                        }),
                    },
                );
            } else {
                if (text.trim().length < 20) {
                    throw new Error(
                        "Paste at least 20 characters of the client requirement.",
                    );
                }
                intake = await api<OpportunityIntakeResponse>(
                    "/opportunities/intake/text",
                    {
                        method: "POST",
                        body: JSON.stringify({
                            text: text.trim(),
                            title: title.trim() || null,
                            client_name: clientName.trim() || null,
                        }),
                    },
                );
            }

            await api<OpportunityAnalysis>(
                `/opportunities/${intake.opportunity.id}/analyze`,
                {
                    method: "POST",
                    timeoutMs: OPPORTUNITY_ANALYSIS_TIMEOUT_MS,
                },
            );

            return api<Opportunity>(`/opportunities/${intake.opportunity.id}`);
        },

        onSuccess: (opportunity) => {
            queryClient.invalidateQueries({
                queryKey: ["opportunities"],
            });

            queryClient.invalidateQueries({
                queryKey: [
                    "opportunity",
                    opportunity.id,
                ],
            });

            queryClient.invalidateQueries({
                queryKey: [
                    "opportunity-analysis",
                    opportunity.id,
                ],
            });
            queryClient.invalidateQueries({
                queryKey: [
                    "opportunity-sources",
                    opportunity.id,
                ],
            });
            queryClient.invalidateQueries({
                queryKey: ["opportunity-roles", opportunity.id],
            });
            queryClient.invalidateQueries({
                queryKey: ["opportunity-teams", opportunity.id],
            });
            queryClient.invalidateQueries({
                queryKey: ["opportunity-gaps", opportunity.id],
            });

            onComplete?.(opportunity);

            if (!opportunityId) {
                navigate(
                    `/opportunities/${opportunity.id}`,
                );
            }
        },
    });

    const canSubmit =
        mode === "url"
            ? Boolean(url.trim())
            : text.trim().length >= 20;

    return (
        <section
            className={
                compact
                    ? "rounded-2xl border border-slate-200 bg-white p-5"
                    : "rounded-3xl bg-ink p-7 text-white shadow-soft md:p-9"
            }
        >
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
                <div>
                    <p
                        className={`text-xs font-bold uppercase tracking-[.2em] ${compact
                            ? "text-evergreen"
                            : "text-mint"
                            }`}
                    >
                        Opportunity intake
                    </p>

                    <h2
                        className={`mt-2 font-serif ${compact
                            ? "text-2xl"
                            : "text-3xl"
                            }`}
                    >
                        {opportunityId
                            ? "Add another source and re-analyze"
                            : "Analyze a client opportunity"}
                    </h2>

                    <p
                        className={`mt-2 max-w-2xl text-sm leading-6 ${compact
                            ? "text-slate-500"
                            : "text-white/55"
                            }`}
                    >
                        Capture the original posting, TOR, RFP or requirement
                        source. Capability Flow preserves the extracted text and
                        prepares the opportunity for capability analysis.
                    </p>
                </div>

                {mutation.isPending && (
                    <div
                        className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold ${compact
                            ? "bg-amber-50 text-amber-700"
                            : "bg-white/10 text-white"
                            }`}
                    >
                        <LoaderCircle
                            size={15}
                            className="animate-spin"
                        />
                        Analyzing…
                    </div>
                )}
            </div>

            {!opportunityId && (
                <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <Field
                        label="Opportunity title (optional)"
                        placeholder="AI can detect this from the source"
                        value={title}
                        onChange={(event) =>
                            setTitle(event.target.value)
                        }
                    />

                    <Field
                        label="Client / organization (optional)"
                        placeholder="AI can detect this too"
                        value={clientName}
                        onChange={(event) =>
                            setClientName(event.target.value)
                        }
                    />
                </div>
            )}

            <div className="mt-6 flex flex-wrap gap-2">
                {(
                    [
                        ["url", "Website URL", Link2],
                        ["text", "Paste text", FileText],
                    ] as const
                ).map(([value, label, Icon]) => (
                    <button
                        key={value}
                        type="button"
                        onClick={() => setMode(value)}
                        className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${mode === value
                            ? compact
                                ? "bg-evergreen text-white"
                                : "bg-white text-ink"
                            : compact
                                ? "bg-slate-100 text-slate-500 hover:text-ink"
                                : "bg-white/10 text-white/60 hover:text-white"
                            }`}
                    >
                        <Icon size={16} />
                        {label}
                    </button>
                ))}
            </div>

            <div className="mt-5">
                {mode === "url" && (
                    <label
                        className={`block text-sm font-medium ${compact
                            ? "text-slate-700"
                            : "text-white/75"
                            }`}
                    >
                        Tender, job, RFP or TOR URL
                        <input
                            type="url"
                            placeholder="https://client.example/opportunity"
                            value={url}
                            onChange={(event) =>
                                setUrl(event.target.value)
                            }
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-ink outline-none focus:border-evergreen focus:ring-2 focus:ring-evergreen/10"
                        />
                    </label>
                )}

                {mode === "text" && (
                    <TextArea
                        label="Client requirement / posting text"
                        rows={9}
                        placeholder="Paste the complete requirement, job posting, TOR or RFP section here."
                        value={text}
                        onChange={(event) =>
                            setText(event.target.value)
                        }
                    />
                )}

            </div>

            {mutation.error && (
                <p className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">
                    {mutation.error.message}
                </p>
            )}

            <div className="mt-6">
                <Button
                    type="button"
                    disabled={
                        mutation.isPending ||
                        !canSubmit
                    }
                    onClick={() =>
                        mutation.mutate()
                    }
                >
                    <Sparkles
                        size={17}
                        className="mr-2 inline"
                    />
                    {mutation.isPending
                        ? "Reading source, extracting requirements and building team…"
                        : opportunityId
                            ? "Add source & re-analyze"
                            : "Analyze opportunity"}
                </Button>
            </div>
        </section>
    );
}

export function OpportunitiesPage() {
    const [search, setSearch] =
        React.useState("");

    const query = useQuery({
        queryKey: ["opportunities"],
        queryFn: () =>
            api<Opportunity[]>(
                "/opportunities",
            ),
    });

    const opportunities =
        (
            query.data ?? []
        ).filter((opportunity) => {
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
        });

    return (
        <div className={wrapper}>
            <PageHeader
                eyebrow="Opportunity intelligence"
                title="Opportunities"
            >
                Capture the client's original source first. Once intelligence
                analysis is configured, the same workspace ranks people, explains
                matches and builds recommended teams.
            </PageHeader>

            <IntakeForm />

            <section className="mt-8">
                <div className="mb-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                    <div>
                        <h2 className="font-serif text-2xl">
                            Opportunity workspace
                        </h2>
                        <p className="mt-1 text-sm text-slate-500">
                            {query.data?.length ?? 0} captured
                            opportunities
                        </p>
                    </div>

                    <div className="flex min-w-[260px] items-center gap-3 rounded-xl border border-slate-200 bg-white px-4">
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
                            placeholder="Search opportunities…"
                            className="w-full bg-transparent py-3 text-sm outline-none"
                        />
                    </div>
                </div>

                {query.isLoading ? (
                    <div className="rounded-2xl bg-white p-8 text-sm text-slate-500">
                        Loading opportunities…
                    </div>
                ) : query.error ? (
                    <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
                        {query.error.message}
                    </p>
                ) : opportunities.length === 0 ? (
                    <EmptyState
                        title="No opportunities yet"
                        text="Paste your first client posting, tender URL, TOR, RFP, or requirement text above."
                    />
                ) : (
                    <div className="grid gap-4">
                        {opportunities.map(
                            (opportunity) => (
                                <Link
                                    key={opportunity.id}
                                    to={`/opportunities/${opportunity.id}`}
                                    className="group rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-0.5 hover:border-evergreen/30 hover:shadow-soft"
                                >
                                    <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <StatusBadge
                                                    value={
                                                        opportunity.status
                                                    }
                                                />

                                                {opportunity.reference_number && (
                                                    <span className="text-xs text-slate-400">
                                                        {
                                                            opportunity.reference_number
                                                        }
                                                    </span>
                                                )}
                                            </div>

                                            <h3 className="mt-3 truncate font-serif text-2xl">
                                                {
                                                    opportunity.title
                                                }
                                            </h3>

                                            <p className="mt-1 text-sm text-slate-500">
                                                {opportunity.client_name ||
                                                    "Client not yet identified"}
                                            </p>
                                        </div>

                                        <div className="flex shrink-0 items-center gap-6">
                                            <div className="text-right">
                                                <p className="text-xs uppercase tracking-wider text-slate-400">
                                                    Deadline
                                                </p>
                                                <p className="mt-1 text-sm font-semibold">
                                                    {formatDate(
                                                        opportunity.deadline_at,
                                                    )}
                                                </p>
                                            </div>

                                            <ArrowRight
                                                size={20}
                                                className="text-slate-300 transition group-hover:translate-x-1 group-hover:text-evergreen"
                                            />
                                        </div>
                                    </div>
                                </Link>
                            ),
                        )}
                    </div>
                )}
            </section>
        </div>
    );
}

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

function RoleWorkspace({
    opportunityId,
    role,
}: {
    opportunityId: string;
    role: OpportunityRole;
}) {
    const query = useQuery({
        queryKey: [
            "role-matches",
            opportunityId,
            role.id,
        ],
        queryFn: () =>
            api<CandidateMatch[]>(
                `/opportunities/${opportunityId}/roles/${role.id}/matches`,
            ),
    });

    return (
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
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

            <div className="mt-5 flex flex-wrap gap-2">
                {role.requirements.map(
                    (requirement) => (
                        <span
                            key={requirement.id}
                            title={
                                requirement.source_excerpt ??
                                undefined
                            }
                            className={`rounded-full px-2.5 py-1 text-xs font-medium ${requirement.importance ===
                                "mandatory"
                                ? "bg-red-50 text-red-700"
                                : requirement.importance ===
                                    "preferred"
                                    ? "bg-amber-50 text-amber-700"
                                    : "bg-slate-100 text-slate-600"
                                }`}
                        >
                            {requirement.label}
                        </span>
                    ),
                )}
            </div>

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
                        {query.data.map(
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

function RecommendedTeams({
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
    const queryClient = useQueryClient();

    const selectTeam = useMutation({
        mutationFn: (teamId: string) =>
            api<Opportunity>(
                `/opportunities/${opportunityId}/teams/${teamId}/select`,
                { method: "POST" },
            ),
        onSuccess: (opportunity) => {
            queryClient.setQueryData(
                ["opportunity", opportunityId],
                opportunity,
            );
            queryClient.invalidateQueries({
                queryKey: ["opportunity-teams", opportunityId],
            });
            queryClient.invalidateQueries({
                queryKey: ["opportunities"],
            });
        },
    });

    const query = useQuery({
        queryKey: [
            "opportunity-teams",
            opportunityId,
        ],
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
                                        className="rounded-xl border border-slate-200 p-4 hover:border-evergreen/30 hover:bg-slate-50"
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
                                    selectTeam.isPending ||
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

function GapsPanel({
    opportunityId,
    analysisStatus,
    rolesCount,
}: {
    opportunityId: string;
    analysisStatus: string | undefined;
    rolesCount: number;
}) {
    const query = useQuery({
        queryKey: [
            "opportunity-gaps",
            opportunityId,
        ],
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

function SourcesPanel({
    opportunityId,
}: {
    opportunityId: string;
}) {
    const queryClient = useQueryClient();
    const query = useQuery({
        queryKey: ["opportunity-sources", opportunityId],
        queryFn: () =>
            api<OpportunitySource[]>(
                `/opportunities/${opportunityId}/sources`,
            ),
    });

    const remove = useMutation({
        mutationFn: (sourceId: string) =>
            api<void>(
                `/opportunities/${opportunityId}/sources/${sourceId}`,
                { method: "DELETE" },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["opportunity-sources", opportunityId],
            });
        },
    });

    if (query.isLoading) {
        return (
            <p className="rounded-2xl bg-white p-5 text-sm text-slate-500">
                Loading captured sources…
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
                title="No sources yet"
                text="Add the original URL or pasted client requirement."
            />
        );
    }

    return (
        <div className="grid gap-3">
            {query.data.map((source) => (
                <article
                    key={source.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5"
                >
                    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                        <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                                <StatusBadge value={source.source_type} />
                                {source.file_size != null && (
                                    <span className="text-xs text-slate-400">
                                        {(source.file_size / 1024).toFixed(1)} KB
                                    </span>
                                )}
                            </div>
                            <p className="mt-3 truncate font-semibold">
                                {source.original_filename ||
                                    source.source_url ||
                                    "Pasted requirement text"}
                            </p>
                            <p className="mt-1 text-xs text-slate-400">
                                Captured {formatDate(source.created_at)}
                            </p>
                        </div>

                        <div className="flex shrink-0 gap-2">
                            {source.stored_filename && (
                                <button
                                    type="button"
                                    onClick={() =>
                                        void apiDownload(
                                            `/opportunities/${opportunityId}/sources/${source.id}/download`,
                                            source.original_filename || "opportunity-source",
                                        )
                                    }
                                    className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold hover:bg-slate-50"
                                >
                                    <Download size={15} />
                                    Snapshot
                                </button>
                            )}
                            <button
                                type="button"
                                disabled={remove.isPending}
                                onClick={() => {
                                    if (window.confirm("Delete this captured source?")) {
                                        remove.mutate(source.id);
                                    }
                                }}
                                className="rounded-xl border border-slate-200 p-2.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                                aria-label="Delete source"
                            >
                                <Trash2 size={16} />
                            </button>
                        </div>
                    </div>
                </article>
            ))}
        </div>
    );
}

export function OpportunityPage() {
    const { opportunityId } =
        useParams();
    const queryClient =
        useQueryClient();
    const navigate = useNavigate();

    const [tab, setTab] =
        React.useState<WorkspaceTab>(
            "overview",
        );

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
            queryKey: [
                "opportunity",
                opportunityId,
            ],
            queryFn: () =>
                api<Opportunity>(
                    `/opportunities/${opportunityId}`,
                ),
            enabled:
                Boolean(opportunityId),
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
            queryKey: [
                "opportunity-analysis",
                opportunityId,
            ],
            queryFn: () =>
                api<OpportunityAnalysis>(
                    `/opportunities/${opportunityId}/analysis`,
                ),
            enabled: shouldLoadAnalysis,
            retry: false,
        });

    const rolesQuery = useQuery({
        queryKey: [
            "opportunity-roles",
            opportunityId,
        ],
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
                    ["opportunity", opportunityId],
                    opportunity,
                );
                queryClient.invalidateQueries({
                    queryKey: ["opportunities"],
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
                    ["opportunity", opportunityId],
                    opportunity,
                );
                queryClient.invalidateQueries({
                    queryKey: ["opportunities"],
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

            onSuccess: () => {
                queryClient.invalidateQueries({
                    queryKey: [
                        "opportunity",
                        opportunityId,
                    ],
                });
                queryClient.invalidateQueries({
                    queryKey: [
                        "opportunity-analysis",
                        opportunityId,
                    ],
                });
                queryClient.invalidateQueries({
                    queryKey: [
                        "opportunity-roles",
                        opportunityId,
                    ],
                });
                queryClient.invalidateQueries({
                    queryKey: [
                        "opportunity-teams",
                        opportunityId,
                    ],
                });
                queryClient.invalidateQueries({
                    queryKey: [
                        "opportunity-gaps",
                        opportunityId,
                    ],
                });
            },
        });

    const opportunity =
        opportunityQuery.data;

    React.useEffect(() => {
        if (!opportunity) {
            return;
        }

        setDetailsForm({
            title: opportunity.title ?? "",
            client_name: opportunity.client_name ?? "",
            reference_number: opportunity.reference_number ?? "",
            deadline_at: opportunity.deadline_at
                ? opportunity.deadline_at.slice(0, 16)
                : "",
            source_url: opportunity.source_url ?? "",
            description: opportunity.description ?? "",
            internal_notes: opportunity.internal_notes ?? "",
            outcome_notes: opportunity.outcome_notes ?? "",
        });
    }, [opportunity]);

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

            <section className="overflow-hidden rounded-3xl bg-ink text-white shadow-soft">
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
                                <p className="mt-5 max-w-3xl text-sm leading-7 text-white/60">
                                    {
                                        analysis.extracted_summary
                                    }
                                </p>
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
                                    disabled={updateStatus.isPending}
                                    onClick={() =>
                                        updateStatus.mutate("pursuing")
                                    }
                                    className="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-ink hover:bg-mint disabled:opacity-50"
                                >
                                    Pursue opportunity
                                </button>

                                <button
                                    type="button"
                                    disabled={updateStatus.isPending}
                                    onClick={() =>
                                        updateStatus.mutate("not_pursuing")
                                    }
                                    className="rounded-xl bg-white/10 px-4 py-2.5 text-sm font-semibold text-white/70 hover:bg-white/15 hover:text-white disabled:opacity-50"
                                >
                                    Do not pursue
                                </button>
                            </>
                        )}

                        {opportunity.status === "pursuing" && (
                            <button
                                type="button"
                                disabled={
                                    updateStatus.isPending ||
                                    !opportunity.selected_team_id
                                }
                                onClick={() =>
                                    updateStatus.mutate("submitted")
                                }
                                className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-ink hover:bg-mint disabled:opacity-50"
                            >
                                <Send size={15} />
                                Mark submitted
                            </button>
                        )}

                        {opportunity.status === "submitted" && (
                            <>
                                <button
                                    type="button"
                                    disabled={updateStatus.isPending}
                                    onClick={() =>
                                        updateStatus.mutate("won")
                                    }
                                    className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-600 disabled:opacity-50"
                                >
                                    <Trophy size={15} />
                                    Mark won
                                </button>

                                <button
                                    type="button"
                                    disabled={updateStatus.isPending}
                                    onClick={() =>
                                        updateStatus.mutate("lost")
                                    }
                                    className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2.5 text-sm font-semibold text-white/70 hover:bg-white/15 hover:text-white disabled:opacity-50"
                                >
                                    <XCircle size={15} />
                                    Mark lost
                                </button>
                            </>
                        )}

                        <button
                            type="button"
                            disabled={reanalyze.isPending}
                            onClick={() => reanalyze.mutate()}
                            className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2.5 text-sm font-semibold text-white/70 hover:bg-white/15 hover:text-white disabled:opacity-50"
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
                                ? "border-mint text-white"
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
                        <section className="rounded-2xl bg-white p-7 shadow-soft">
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
                                            <p className="text-xs font-bold uppercase tracking-[.16em] text-slate-400">
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
                                            <p className="text-xs font-bold uppercase tracking-[.16em] text-slate-400">
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
                            <div className="rounded-2xl border border-slate-200 bg-white p-6">
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
                                {roles.map((role) => (
                                    <RoleWorkspace
                                        key={role.id}
                                        opportunityId={
                                            opportunityId
                                        }
                                        role={role}
                                    />
                                ))}
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
                        <section className="rounded-2xl border border-slate-200 bg-white p-6">
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

                                {!editingDetails && (
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
                                            disabled={saveDetails.isPending}
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
                                            disabled={saveDetails.isPending}
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
                                <p className="text-xs font-bold uppercase tracking-[.16em] text-slate-400">
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
                                        queryKey: [
                                            "opportunity-roles",
                                            opportunityId,
                                        ],
                                    });
                                    setTab(
                                        "overview",
                                    );
                                }}
                            />
                        </div>

                        <aside className="rounded-2xl border border-slate-200 bg-white p-6">
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
