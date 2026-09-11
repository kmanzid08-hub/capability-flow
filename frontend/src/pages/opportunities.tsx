import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BriefcaseBusiness, GitBranch, Plus, RefreshCw, Search } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { PageHeader } from "../components/ui";
import { EmptyState } from "../components/ui/EmptyState";
import { Modal } from "../components/ui/Modal";
import { Pagination } from "../components/ui/Pagination";
import { Skeleton } from "../components/ui/Skeleton";
import { IntakeForm } from "../features/opportunities/IntakeForm";
import { api } from "../lib/api";
import { qk } from "../lib/queryKeys";
import { useWorkspace } from "../lib/workspace";
import type { Opportunity } from "../types";
export function OpportunitiesPage() {
  const query = useQuery({ queryKey: qk("opportunities"), queryFn: ({ signal }) => api<Opportunity[]>("/opportunities", { signal }) });
  const [params, setParams] = useSearchParams(); const { canWrite } = useWorkspace();
  const [busy, setBusy] = useState(false); const [page, setPage] = useState(1);
  const search = params.get("q") ?? ""; const status = params.get("status") ?? ""; const isNew = params.get("new") === "1";
  const update = (key: string, value: string) => { setPage(1); setParams((current) => { const next = new URLSearchParams(current); if (value) next.set(key, value); else next.delete(key); return next; }, { replace: true }); };
  const items = (query.data ?? []).filter((o) => (!status || o.status === status) && `${o.title} ${o.client_name ?? ""} ${o.reference_number ?? ""}`.toLowerCase().includes(search.toLowerCase())).sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  const currentPage = Math.min(page, Math.max(1, Math.ceil(items.length / 20)));
  return <div className="cf-page"><PageHeader eyebrow="From requirement to the right team" title="Opportunities" action={<div className="flex gap-2"><Link className="cf-button cf-button-secondary" to="/pipeline"><GitBranch size={14} />Pipeline</Link>{canWrite && <button className="cf-button cf-button-primary" onClick={() => update("new", "1")}><Plus size={15} />New opportunity</button>}</div>}>Capture a brief. Understand the requirements. Find your team.</PageHeader>
    <div className="cf-toolbar"><label className="cf-search"><Search size={16} /><input aria-label="Search opportunities" placeholder="Search opportunity, client or reference..." value={search} onChange={(e) => update("q", e.target.value)} /></label><div className="flex gap-2 items-center"><select className="cf-select" aria-label="Filter opportunities by status" value={status} onChange={(e) => update("status", e.target.value)}><option value="">All statuses</option>{["new", "analyzing", "needs_review", "ready", "pursuing", "submitted", "won", "lost", "not_pursuing", "archived"].map((value) => <option value={value} key={value}>{value.replaceAll("_", " ")}</option>)}</select><button className="cf-icon-button" aria-label="Refresh opportunities" disabled={query.isFetching} onClick={() => void query.refetch()}><RefreshCw size={15} className={query.isFetching ? "animate-spin" : ""} /></button></div></div>
    {query.error && <p className="cf-alert cf-alert-error mb-5" role="alert">{query.error.message}</p>}
    <div className="cf-table-wrap">{query.isPending ? <Skeleton rows={6} /> : items.length ? <><div className="overflow-x-auto"><table className="cf-table"><thead><tr><th>Opportunity</th><th>Status</th><th className="hidden md:table-cell">Deadline</th><th className="hidden lg:table-cell">Updated</th><th><span className="sr-only">Open</span></th></tr></thead><tbody>{items.slice((currentPage - 1) * 20, currentPage * 20).map((o) => <tr key={o.id}><td><div className="flex items-center gap-3"><div className="cf-avatar hidden sm:inline-flex"><BriefcaseBusiness size={16} /></div><div><Link className="font-medium hover:underline" to={`/opportunities/${o.id}`}>{o.title}</Link><p className="text-xs text-slate-400 mt-1">{[o.client_name, o.reference_number].filter(Boolean).join(" / ") || "Client not recorded"}</p></div></div></td><td><StatusBadge value={o.status} /></td><td className="hidden md:table-cell text-slate-500">{o.deadline_at ? new Date(o.deadline_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "Not recorded"}</td><td className="hidden lg:table-cell text-slate-400">{new Date(o.updated_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</td><td><Link to={`/opportunities/${o.id}`} className="cf-icon-button" aria-label={`Open ${o.title}`}><ArrowUpRight size={15} /></Link></td></tr>)}</tbody></table></div><Pagination page={currentPage} pageSize={20} total={items.length} onChange={setPage} /></> : <EmptyState title={query.data?.length ? "No matching opportunities" : "A clear start for your next bid"} description={query.data?.length ? "Try a different search or status." : "Add a tender, TOR, or client brief to assess your team's fit."} action={canWrite && <button className="cf-button cf-button-primary" onClick={() => update("new", "1")}><Plus size={14} />New opportunity</button>} />}</div>
    {isNew && canWrite && <Modal title="New opportunity" wide busy={busy} onClose={() => update("new", "")}><IntakeForm compact onBusyChange={setBusy} /></Modal>}
  </div>;
}
