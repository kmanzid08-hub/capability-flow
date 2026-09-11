import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ArrowUpRight, BriefcaseBusiness, CalendarDays, CircleCheck, Plus, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { PageHeader } from "../components/ui";
import { EmptyState } from "../components/ui/EmptyState";
import { Skeleton } from "../components/ui/Skeleton";
import { api } from "../lib/api";
import { qk } from "../lib/queryKeys";
import { useWorkspace } from "../lib/workspace";
import type { Opportunity, PeoplePage } from "../types";

function date(value: string | null) { return value ? new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "No deadline"; }
export function ManagementDashboardPage() {
  const { user, canWrite } = useWorkspace();
  const opportunitiesQuery = useQuery({ queryKey: qk("opportunities"), queryFn: ({ signal }) => api<Opportunity[]>("/opportunities", { signal }) });
  const peopleQuery = useQuery({ queryKey: qk("people", "count"), queryFn: ({ signal }) => api<PeoplePage>("/people?limit=1", { signal }) });
  const opportunities = opportunitiesQuery.data ?? [];
  const active = opportunities.filter((o) => !["won", "lost", "archived", "not_pursuing"].includes(o.status));
  const review = opportunities.filter((o) => o.status === "needs_review" || o.status === "ready");
  const submitted = opportunities.filter((o) => o.status === "submitted");
  const upcoming = active.filter((o) => o.deadline_at).sort((a, b) => new Date(a.deadline_at!).getTime() - new Date(b.deadline_at!).getTime()).slice(0, 4);
  const recent = [...opportunities].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at)).slice(0, 6);
  const name = user.data?.full_name.trim().split(/\s+/)[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const counts = opportunitiesQuery.data ? [active.length, review.length, submitted.length] : [null, null, null];
  return <div className="cf-page"><PageHeader eyebrow="Your workspace at a glance" title={`${greeting}${name ? `, ${name}` : ""}.`} action={canWrite && <Link className="cf-button cf-button-primary" to="/opportunities?new=1"><Plus size={15} />New opportunity</Link>}>A clear view of your people and the work ahead.</PageHeader>
    {(opportunitiesQuery.error || peopleQuery.error) && <p className="cf-alert cf-alert-error mb-6">Some workspace data could not load. <button className="underline" onClick={() => { void opportunitiesQuery.refetch(); void peopleQuery.refetch(); }}>Try again</button></p>}
    <div className="cf-stat-grid">{[
      { label: "People", value: peopleQuery.data?.total, foot: "In your directory", to: "/people" },
      { label: "Active opportunities", value: counts[0], foot: "From intake to submission", to: "/pipeline" },
      { label: "Needs a decision", value: counts[1], foot: "Review or ready to pursue", to: "/pipeline" },
      { label: "Submitted", value: counts[2], foot: "Awaiting an outcome", to: "/opportunities?status=submitted" },
    ].map((stat) => <Link key={stat.label} to={stat.to} className="cf-stat group"><div className="flex justify-between items-center"><p className="cf-stat-label">{stat.label}</p><ArrowUpRight size={14} className="text-slate-300 group-hover:text-slate-500" /></div><p className="cf-stat-value">{stat.value ?? "\u2014"}</p><p className="cf-stat-foot">{stat.foot}</p></Link>)}</div>
    <div className="grid gap-6 xl:grid-cols-[1.55fr_1fr]">
      <section className="cf-panel"><div className="cf-panel-heading"><h2>Coming up</h2><CalendarDays size={17} className="text-slate-400" /></div>{opportunitiesQuery.isPending ? <Skeleton rows={3} /> : upcoming.length ? <div>{upcoming.map((item) => { const days = Math.ceil((Date.parse(item.deadline_at!) - Date.now()) / 86400000); return <Link to={`/opportunities/${item.id}`} key={item.id} className="flex items-center justify-between gap-6 py-4 border-b border-slate-100 last:border-0 group"><div className="min-w-0"><p className="text-sm font-medium truncate group-hover:underline">{item.title}</p><p className="text-xs text-slate-400 mt-1">{item.client_name ?? "Client not recorded"}</p></div><div className="text-right shrink-0"><p className="text-xs font-medium">{date(item.deadline_at)}</p><p className={`text-[11px] mt-1 ${days <= 3 ? "text-amber-700" : "text-slate-400"}`}>{days < 0 ? "Deadline passed" : days === 0 ? "Due today" : `${days} day${days === 1 ? "" : "s"} left`}</p></div></Link>; })}</div> : <EmptyState title="Nothing due right now" description="Opportunity deadlines will appear here when they are recorded." />}</section>
      <section className="cf-panel"><div className="cf-panel-heading"><h2>Needs your attention</h2><CircleCheck size={17} className="text-slate-400" /></div>{opportunitiesQuery.isPending ? <Skeleton rows={3} /> : review.length ? <div className="space-y-3">{review.slice(0, 3).map((item) => <Link to={`/opportunities/${item.id}`} key={item.id} className="block rounded-xl border border-slate-100 p-4 hover:bg-slate-50"><StatusBadge value={item.status} /><p className="font-medium text-sm mt-2">{item.title}</p></Link>)}</div> : <EmptyState title="You're up to date" description="Opportunities awaiting review or a pursuit decision will appear here." />}<Link className="cf-link mt-5" to="/pipeline">Open pipeline<ArrowRight size={14} /></Link></section>
    </div>
    <section className="cf-table-wrap mt-6"><div className="cf-panel-heading px-6 pt-6"><h2>Recent opportunities</h2><Link className="cf-link" to="/opportunities">View all<ArrowRight size={14} /></Link></div>{opportunitiesQuery.isPending ? <Skeleton rows={4} /> : recent.length ? <div className="overflow-x-auto"><table className="cf-table"><thead><tr><th>Opportunity</th><th>Status</th><th className="hidden sm:table-cell">Deadline</th><th className="hidden md:table-cell">Updated</th><th><span className="sr-only">Open</span></th></tr></thead><tbody>{recent.map((item) => <tr key={item.id}><td><Link className="font-medium hover:underline" to={`/opportunities/${item.id}`}>{item.title}</Link><p className="text-xs text-slate-400 mt-1">{item.client_name}</p></td><td><StatusBadge value={item.status} /></td><td className="hidden sm:table-cell text-slate-500">{date(item.deadline_at)}</td><td className="hidden md:table-cell text-slate-400">{date(item.updated_at)}</td><td><Link aria-label={`Open ${item.title}`} to={`/opportunities/${item.id}`} className="cf-icon-button"><ArrowUpRight size={16} /></Link></td></tr>)}</tbody></table></div> : <EmptyState title="Your next opportunity starts here" description="Add a tender, TOR, or client requirement to understand who is ready to deliver." action={canWrite && <Link className="cf-button cf-button-primary" to="/opportunities?new=1">Add an opportunity</Link>} />}</section>
    <div className="mt-7 flex flex-wrap gap-6 text-xs text-slate-400"><Link to="/people" className="flex items-center gap-2 hover:text-ink"><Users size={14} />Manage your people</Link><Link to="/opportunities" className="flex items-center gap-2 hover:text-ink"><BriefcaseBusiness size={14} />Explore opportunities</Link></div>
  </div>;
}
