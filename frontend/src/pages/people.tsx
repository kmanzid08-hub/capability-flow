import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, LayoutGrid, List, MapPin, Plus, RefreshCw, Search } from "lucide-react";
import { useDeferredValue, useMemo, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { PageHeader } from "../components/ui";
import { Avatar } from "../components/ui/Avatar";
import { EmptyState } from "../components/ui/EmptyState";
import { Pagination } from "../components/ui/Pagination";
import { Skeleton } from "../components/ui/Skeleton";
import { api } from "../lib/api";
import { directoryOptions, filterPeople } from "../lib/people";
import { qk } from "../lib/queryKeys";
import { useWorkspace } from "../lib/workspace";
import type { Person } from "../types";
export function PeoplePage() {
  const [params, setParams] = useSearchParams();
  const query = useQuery(directoryOptions()); const queryClient = useQueryClient();
  const { canWrite } = useWorkspace(); const searchInput = useRef<HTMLInputElement>(null);
  const search = params.get("q") ?? ""; const term = useDeferredValue(search);
  const availability = params.get("availability") ?? ""; const country = params.get("country") ?? "";
  const sort = params.get("sort") ?? "name"; const view = params.get("view") ?? "list";
  const pageSize = params.get("size") === "50" ? 50 : 25;
  const requestedPage = Math.max(1, Math.floor(Number(params.get("page"))) || 1);
  const update = (key: string, value: string, reset = true) => setParams((current) => { const next = new URLSearchParams(current); if (value) next.set(key, value); else next.delete(key); if (reset) next.delete("page"); return next; }, { replace: true });
  const countries = useMemo(() => [...new Set((query.data ?? []).map((p) => p.country_of_residence).filter((v): v is string => Boolean(v)))].sort(), [query.data]);
  const filtered = useMemo(() => filterPeople(query.data ?? [], term, availability, country).sort((a, b) => sort === "updated" ? Date.parse(b.updated_at) - Date.parse(a.updated_at) : a.display_name.localeCompare(b.display_name)), [query.data, term, availability, country, sort]);
  const page = Math.min(requestedPage, Math.max(1, Math.ceil(filtered.length / pageSize)));
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize);
  const prefetch = (id: string) => { void queryClient.prefetchQuery({ queryKey: qk("person", id), queryFn: ({ signal }) => api<Person>(`/people/${id}`, { signal }), staleTime: 60_000 }); };
  return <div className="cf-page"><PageHeader eyebrow="Your talent directory" title="People" action={canWrite && <Link to="/people/new" className="cf-button cf-button-primary"><Plus size={15} />Add person</Link>}>The people and expertise behind your next project.</PageHeader>
    <div className="cf-toolbar"><label className="cf-search"><Search size={17} /><input ref={searchInput} value={search} onChange={(e) => update("q", e.target.value)} placeholder="Search name, title, country, email..." aria-label="Search people" />{search && <button className="text-slate-400 px-1" aria-label="Clear search" onClick={() => update("q", "")}>x</button>}</label>
      <div className="flex flex-wrap items-center gap-2"><select className="cf-select" aria-label="Filter by availability" value={availability} onChange={(e) => update("availability", e.target.value)}><option value="">All availability</option><option value="available">Available</option><option value="partially_available">Partially available</option><option value="unavailable">Unavailable</option><option value="unknown">Not recorded</option></select><select className="cf-select" aria-label="Filter by country" value={country} onChange={(e) => update("country", e.target.value)}><option value="">All countries</option>{countries.map((value) => <option key={value}>{value}</option>)}</select><select className="cf-select" aria-label="Sort people" value={sort} onChange={(e) => update("sort", e.target.value)}><option value="name">Name A-Z</option><option value="updated">Recently updated</option></select><div className="cf-view-toggle"><button aria-label="List view" aria-pressed={view === "list"} onClick={() => update("view", "list", false)}><List size={16} /></button><button aria-label="Grid view" aria-pressed={view === "grid"} onClick={() => update("view", "grid", false)}><LayoutGrid size={15} /></button></div><button className="cf-icon-button" aria-label="Refresh people" onClick={() => void query.refetch()} disabled={query.isFetching}><RefreshCw size={15} className={query.isFetching ? "animate-spin" : ""} /></button></div></div>
    <div className="flex justify-between mb-3"><p className="text-xs text-slate-400" aria-live="polite">{query.isPending ? "Loading your directory..." : `${filtered.length} ${filtered.length === 1 ? "person" : "people"}${search || availability || country ? ` of ${query.data?.length ?? 0}` : " in your workspace"}`}</p>{(search || availability || country) && <button className="text-xs text-slate-500 hover:text-ink" onClick={() => setParams({ view, sort })}>Clear filters</button>}</div>
    {query.error && <p role="alert" className="cf-alert cf-alert-error mb-4">{query.error.message} <button className="underline" onClick={() => void query.refetch()}>Retry</button></p>}
    {query.isPending ? <div className="cf-table-wrap"><Skeleton rows={7} title="Loading people" /></div> : !visible.length ? <div className="cf-panel"><EmptyState title={query.data?.length ? "No matching people" : "Build your talent directory"} description={query.data?.length ? "Try a different name or clear the filters." : "Add a person, then upload their CV and supporting evidence."} action={canWrite && !query.data?.length && <Link className="cf-button cf-button-primary" to="/people/new">Add your first person</Link>} /></div> : <>
      {view === "grid" ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{visible.map((person) => <Link key={person.id} to={`/people/${person.id}`} onMouseEnter={() => prefetch(person.id)} onFocus={() => prefetch(person.id)} className="cf-panel group hover:border-slate-300"><div className="flex items-start justify-between"><Avatar name={person.display_name} /><ArrowUpRight size={16} className="text-slate-300 group-hover:text-ink" /></div><h2 className="font-semibold mt-5 text-[15px]">{person.display_name}</h2><p className="text-xs text-slate-500 mt-1 min-h-8">{person.professional_title || "Title not recorded"}</p><div className="flex items-center justify-between gap-3 mt-5"><span className="text-[11px] text-slate-400 flex items-center gap-1.5"><MapPin size={12} />{person.country_of_residence || "Not recorded"}</span><StatusBadge value={person.availability_status} /></div></Link>)}</div> : <div className="cf-table-wrap"><div className="overflow-x-auto"><table className="cf-table"><thead><tr><th>Person</th><th className="hidden md:table-cell">Location</th><th>Availability</th><th className="hidden lg:table-cell">Profile</th><th><span className="sr-only">Open profile</span></th></tr></thead><tbody>{visible.map((person) => <tr key={person.id} onMouseEnter={() => prefetch(person.id)}><td><div className="flex items-center gap-3"><Avatar name={person.display_name} /><div className="min-w-0"><Link className="font-medium hover:underline text-[13px]" to={`/people/${person.id}`} onFocus={() => prefetch(person.id)}>{person.display_name}</Link><p className="mt-1 text-xs text-slate-400 max-w-xs truncate">{person.professional_title || "Title not recorded"}</p></div></div></td><td className="hidden md:table-cell text-slate-500">{person.country_of_residence || "\u2014"}</td><td><StatusBadge value={person.availability_status} /></td><td className="hidden lg:table-cell"><StatusBadge value={person.profile_status} /></td><td><Link to={`/people/${person.id}`} className="cf-icon-button" aria-label={`Open ${person.display_name}`}><ArrowUpRight size={15} /></Link></td></tr>)}</tbody></table></div></div>}
      <Pagination page={page} total={filtered.length} pageSize={pageSize} onChange={(n) => update("page", String(n), false)} onSizeChange={(n) => update("size", String(n))} />
    </>}
    {!query.isPending && !query.error && <p className="mt-5 text-[11px] text-slate-400">Search covers names, titles, locations and email addresses across the loaded workspace directory.</p>}
  </div>;
}
