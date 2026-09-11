import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArrowLeft, ArrowUpRight, Check, Mail, MapPin, Pencil, Phone, Upload } from "lucide-react";
import { lazy, Suspense, useEffect, useState, type ChangeEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Field, TextArea } from "../components/ui";
import { Avatar } from "../components/ui/Avatar";
import { Modal } from "../components/ui/Modal";
import { PageSkeleton, Skeleton } from "../components/ui/Skeleton";
import { api } from "../lib/api";
import { qk } from "../lib/queryKeys";
import { useWorkspace } from "../lib/workspace";
import type { Person, ProfileCompleteness } from "../types";

const Skills = lazy(() => import("../features/profile/SkillPanel").then((m) => ({ default: m.SkillPanel })));
const Education = lazy(() => import("../features/profile/EducationPanel").then((m) => ({ default: m.EducationPanel })));
const Certifications = lazy(() => import("../features/profile/CertificationPanel").then((m) => ({ default: m.CertificationPanel })));
const Work = lazy(() => import("../features/profile/WorkExperiencePanel").then((m) => ({ default: m.WorkExperiencePanel })));
const Projects = lazy(() => import("../features/profile/ProjectsPanel").then((m) => ({ default: m.ProjectsPanel })));
const Documents = lazy(() => import("../features/documents/DocumentsPanel").then((m) => ({ default: m.DocumentsPanel })));
const tabs = [
  ["overview", "Overview"], ["work", "Experience"], ["projects", "Projects"], ["education", "Education"], ["skills", "Skills"], ["certifications", "Credentials"], ["documents", "Documents"], ["review", "AI review"],
] as const;
type Tab = typeof tabs[number][0];
const isTab = (value: string | null): value is Tab => tabs.some(([id]) => id === value);

function ProfileEditor({ person, onClose }: { person: Person; onClose: () => void; }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ first_name: person.first_name, middle_name: person.middle_name ?? "", last_name: person.last_name, professional_title: person.professional_title ?? "", primary_email: person.primary_email ?? "", primary_phone: person.primary_phone ?? "", country_of_residence: person.country_of_residence ?? "", nationality: person.nationality ?? "", availability_status: person.availability_status, profile_status: person.profile_status, summary: person.summary ?? "" });
  const update = useMutation({ mutationFn: () => api<Person>(`/people/${person.id}`, { method: "PATCH", body: JSON.stringify(Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value.trim() || null]))) }), onSuccess: (value) => { queryClient.setQueryData(qk("person", person.id), value); void queryClient.invalidateQueries({ queryKey: qk("people") }); void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", person.id) }); onClose(); } });
  const field = (key: keyof typeof form) => ({ value: form[key], onChange: (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setForm((old) => ({ ...old, [key]: event.target.value })) });
  return <Modal title="Edit profile" onClose={onClose} wide busy={update.isPending}><form onSubmit={(e) => { e.preventDefault(); update.mutate(); }} className="space-y-5"><div className="grid gap-4 sm:grid-cols-2"><Field label="First name" required {...field("first_name")} /><Field label="Last name" required {...field("last_name")} /><Field label="Middle name" {...field("middle_name")} /><Field label="Professional title" {...field("professional_title")} /><Field label="Email" type="email" {...field("primary_email")} /><Field label="Phone" {...field("primary_phone")} /><Field label="Country of residence" {...field("country_of_residence")} /><Field label="Nationality" {...field("nationality")} /><label className="cf-field"><span>Availability</span><select className="cf-input" {...field("availability_status")}><option value="unknown">Not recorded</option><option value="available">Available</option><option value="partially_available">Partially available</option><option value="unavailable">Unavailable</option></select></label><label className="cf-field"><span>Profile status</span><select className="cf-input" {...field("profile_status")}><option value="draft">Draft</option><option value="active">Active</option></select></label></div><TextArea label="Professional summary" rows={4} {...field("summary")} />{update.error && <p role="alert" className="cf-alert cf-alert-error">{update.error.message}</p>}<div className="flex justify-end gap-2"><Button secondary onClick={onClose} disabled={update.isPending}>Cancel</Button><Button type="submit" disabled={update.isPending}>{update.isPending ? "Saving..." : "Save changes"}</Button></div></form></Modal>;
}

export function PersonPage() {
  const { personId = "" } = useParams();
  return <ProfileWorkspace key={personId} personId={personId} />;
}
function ProfileWorkspace({ personId }: { personId: string; }) {
  const [params, setParams] = useSearchParams(); const queryClient = useQueryClient();
  const { canWrite } = useWorkspace();
  const value = params.get("tab"); const tab: Tab = isTab(value) ? value : "overview";
  const [visited, setVisited] = useState<Set<string>>(() => new Set([tab]));
  const [editing, setEditing] = useState(false); const [archived, setArchived] = useState(false);
  useEffect(() => { setVisited((old) => old.has(tab) ? old : new Set([...old, tab])); }, [tab]);
  const query = useQuery({ queryKey: qk("person", personId), queryFn: ({ signal }) => api<Person>(`/people/${personId}`, { signal }), enabled: Boolean(personId) });
  const completeness = useQuery({ queryKey: qk("profile-completeness", personId), queryFn: ({ signal }) => api<ProfileCompleteness>(`/people/${personId}/completeness`, { signal }), enabled: Boolean(query.data) });
  const archive = useMutation({ mutationFn: () => api<void>(`/people/${personId}`, { method: "DELETE" }), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: qk("people") }); setArchived(true); } });
  const select = (id: Tab) => setParams(id === "overview" ? {} : { tab: id });
  if (query.isPending) return <PageSkeleton />;
  if (!query.data || query.error) return <div className="cf-page"><p className="cf-alert cf-alert-error">{query.error?.message ?? "Person not found."}</p><Link to="/people" className="cf-link mt-5">Back to people</Link></div>;
  const person = query.data;
  if (archived) return <div className="cf-page"><div className="cf-panel text-center py-14"><Check className="mx-auto mb-4 text-slate-400" /><h1 className="text-2xl font-semibold">Profile archived</h1><p className="text-slate-500 mt-3">The record is retained for audit history.</p><Link className="cf-button cf-button-primary mt-6" to="/people">Return to people</Link></div></div>;
  const sections = completeness.data?.sections;
  const docsVisited = visited.has("documents") || visited.has("review") || tab === "documents" || tab === "review";
  return <div className="cf-page"><Link to="/people" className="cf-link text-slate-400 mb-7"><ArrowLeft size={14} />People</Link><header className="cf-profile-header flex flex-wrap items-start justify-between gap-6"><div className="flex gap-5 items-center"><Avatar name={person.display_name} large /><div><h1 className="text-[28px] font-semibold tracking-tight leading-tight">{person.display_name}</h1><p className="text-sm text-slate-500 mt-2">{person.professional_title || "Professional title not recorded"}</p><div className="flex gap-3 items-center flex-wrap mt-3"><StatusBadge value={person.availability_status} />{person.country_of_residence && <span className="text-xs text-slate-400 flex items-center gap-1"><MapPin size={12} />{person.country_of_residence}</span>}</div></div></div><div className="flex gap-2">{canWrite && <><Button secondary onClick={() => setEditing(true)}><Pencil size={14} />Edit profile</Button><Button onClick={() => select("documents")}><Upload size={14} />Add evidence</Button></>}</div></header>
    <nav className="cf-tabs" aria-label="Profile sections">{tabs.map(([id, label]) => <button key={id} type="button" aria-current={tab === id ? "page" : undefined} onClick={() => select(id)}>{label}</button>)}</nav>
    {tab === "overview" && <div className="cf-profile-overview"><section className="cf-panel"><div className="cf-panel-heading"><h2>Professional summary</h2>{canWrite && <button className="cf-icon-button" aria-label="Edit summary" onClick={() => setEditing(true)}><Pencil size={14} /></button>}</div><p className="text-sm leading-7 text-slate-600 whitespace-pre-line">{person.summary || "No summary yet. Add one manually or analyze supporting evidence to create suggestions."}</p><div className="border-t border-slate-100 mt-8 pt-6 grid gap-5 sm:grid-cols-2"><div><p className="text-[11px] text-slate-400 mb-1.5">Email</p><p className="text-sm break-all">{person.primary_email ? <a href={`mailto:${person.primary_email}`} className="flex items-center gap-2"><Mail size={13} className="text-slate-400" />{person.primary_email}</a> : "Not recorded"}</p></div><div><p className="text-[11px] text-slate-400 mb-1.5">Phone</p><p className="text-sm">{person.primary_phone ? <a href={`tel:${person.primary_phone}`} className="flex items-center gap-2"><Phone size={13} className="text-slate-400" />{person.primary_phone}</a> : "Not recorded"}</p></div><div><p className="text-[11px] text-slate-400 mb-1.5">Nationality</p><p>{person.nationality || "Not recorded"}</p></div><div><p className="text-[11px] text-slate-400 mb-1.5">Profile status</p><StatusBadge value={person.profile_status} /></div></div></section><aside className="cf-panel"><div className="cf-panel-heading"><h2>Profile readiness</h2><span className="text-2xl tracking-tight font-semibold">{completeness.data ? `${completeness.data.profile_percent}%` : "\u2014"}</span></div><p className="text-xs text-slate-400 leading-6 mb-5">Completeness measures recorded information, not verification of qualifications.</p>{sections && <div className="space-y-3">{Object.entries(sections).map(([key, complete]) => <div key={key} className="flex items-center justify-between text-xs"><span className="capitalize text-slate-500">{key.replaceAll("_", " ")}</span>{complete ? <Check size={14} className="text-emerald-600" /> : <span className="text-slate-300">Not recorded</span>}</div>)}</div>}<div className="mt-6 pt-5 border-t border-slate-100 flex justify-between"><p className="text-xs text-slate-500">Evidence-linked records</p><p className="text-xs font-medium">{completeness.data?.evidence_backed_records ?? "\u2014"} / {completeness.data?.total_structured_records ?? "\u2014"}</p></div><button className="cf-link mt-5" onClick={() => select("review")}>Review AI suggestions<ArrowUpRight size={14} /></button></aside></div>}
    <Suspense fallback={<Skeleton rows={4} />}>
      {(visited.has("skills") || tab === "skills") && <div hidden={tab !== "skills"}><Skills personId={personId} /></div>}
      {(visited.has("education") || tab === "education") && <div hidden={tab !== "education"}><Education personId={personId} /></div>}
      {(visited.has("certifications") || tab === "certifications") && <div hidden={tab !== "certifications"}><Certifications personId={personId} /></div>}
      {(visited.has("work") || tab === "work") && <div hidden={tab !== "work"}><Work personId={personId} /></div>}
      {(visited.has("projects") || tab === "projects") && <div hidden={tab !== "projects"}><Projects personId={personId} /></div>}
      {docsVisited && <div hidden={tab !== "documents" && tab !== "review"}><Documents personId={personId} view={tab === "review" ? "review" : "documents"} /></div>}
    </Suspense>
    {tab === "overview" && canWrite && <div className="mt-9 flex justify-between items-center gap-3"><p className="text-[11px] text-slate-400">Updated {new Date(person.updated_at).toLocaleDateString()}</p><button className="cf-link text-slate-400" disabled={archive.isPending} onClick={() => { if (window.confirm(`Archive ${person.display_name}? The record will leave the active directory but its history will be retained.`)) archive.mutate(); }}><Archive size={13} />{archive.isPending ? "Archiving..." : "Archive profile"}</button></div>}
    {archive.error && <p className="cf-alert cf-alert-error mt-4">{archive.error.message}</p>}
    {editing && <ProfileEditor person={person} onClose={() => setEditing(false)} />}
  </div>;
}
