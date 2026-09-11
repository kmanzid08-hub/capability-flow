import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BriefcaseBusiness, ChevronsUpDown, GitBranch, Layers2, LayoutDashboard, LogOut, PanelLeftClose, PanelLeftOpen, Plus, Search, Settings2, Users, WifiOff } from "lucide-react";
import { Suspense, useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { session } from "../lib/session";
import { useWorkspace } from "../lib/workspace";
import { ErrorBoundary } from "./ErrorBoundary";
import { CommandPalette } from "./layout/CommandPalette";
import { Button, Field } from "./ui";
import { Avatar } from "./ui/Avatar";
import { Modal } from "./ui/Modal";
import { PageSkeleton } from "./ui/Skeleton";

const navItems = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/people", label: "People", icon: Users, end: false },
  { to: "/opportunities", label: "Opportunities", icon: BriefcaseBusiness, end: false },
  { to: "/pipeline", label: "Pipeline", icon: GitBranch, end: false },
  { to: "/organization", label: "Settings", icon: Settings2, end: false },
];
function slugify(value: string) { return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, ""); }
export function AppLayout() {
  const navigate = useNavigate(); const location = useLocation(); const queryClient = useQueryClient();
  const snapshot = useSyncExternalStore(session.subscribe, session.snapshot, () => "");
  const previousToken = useRef(session.token());
  useEffect(() => {
    if (previousToken.current !== session.token()) {
      previousToken.current = session.token();
      void queryClient.cancelQueries().then(() => queryClient.clear());
    }
  }, [snapshot, queryClient]);
  const { user, membership } = useWorkspace();
  const [commandOpen, setCommandOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState(""); const [slug, setSlug] = useState("");
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("cf-sidebar-collapsed") === "1");
  const [offline, setOffline] = useState(!navigator.onLine);
  const active = navItems.find((item) => item.end ? location.pathname === item.to : location.pathname.startsWith(item.to));
  const closeCommand = useCallback(() => setCommandOpen(false), []);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setCommandOpen((v) => !v); } };
    const on = () => setOffline(false); const off = () => setOffline(true);
    document.addEventListener("keydown", handler); window.addEventListener("online", on); window.addEventListener("offline", off);
    return () => { document.removeEventListener("keydown", handler); window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);
  useEffect(() => { document.title = `${active?.label ?? "Workspace"} - Capability Flow`; }, [active?.label]);
  const switchWorkspace = async (id: string) => {
    if (!id || id === session.organization()) return;
    await queryClient.cancelQueries(); queryClient.clear(); session.setOrganization(id); navigate("/", { replace: true });
  };
  const create = useMutation({ mutationFn: () => api<{ id: string; }>("/organizations", { method: "POST", body: JSON.stringify({ name: name.trim(), slug: slug.trim() }) }), onSuccess: async (workspace) => { setCreating(false); setName(""); setSlug(""); await switchWorkspace(workspace.id); } });
  const logout = async () => { await queryClient.cancelQueries(); queryClient.clear(); session.clear(); navigate("/login", { replace: true }); };
  return <div className={`cf-shell ${collapsed ? "cf-shell-collapsed" : ""}`}>
    <a href="#workspace-main" className="cf-skip-link">Skip to content</a>
    <aside className="cf-sidebar">
      <NavLink to="/" className="cf-brand" aria-label="Capability Flow home"><span className="cf-logo"><Layers2 size={16} strokeWidth={1.8} /></span><span className="cf-sidebar-label">Capability<span className="font-normal text-slate-400"> Flow</span></span></NavLink>
      <div className="cf-workspace-switch"><div className="flex items-center gap-2"><ChevronsUpDown size={14} className="text-slate-400 shrink-0" /><select aria-label="Current workspace" value={session.organization() ?? ""} onChange={(e) => void switchWorkspace(e.target.value)}>
        {!user.data?.memberships.length && <option value={session.organization() ?? ""}>{user.isPending ? "Loading workspace..." : "Workspace"}</option>}
        {user.data?.memberships.map((m) => <option key={m.organization_id} value={m.organization_id}>{m.organization_name}</option>)}
      </select></div><button className="cf-new-workspace cf-sidebar-label" onClick={() => { create.reset(); setCreating(true); }}><Plus size={13} />New workspace</button></div>
      <p className="cf-nav-label cf-sidebar-label">WORKSPACE</p>
      <nav className="cf-navigation" aria-label="Primary navigation">{navItems.map(({ icon: Icon, ...item }) => <NavLink key={item.to} to={item.to} end={item.end} title={collapsed ? item.label : undefined} className={({ isActive }) => `cf-nav-item ${isActive ? "cf-nav-active" : ""}`}><Icon size={18} strokeWidth={1.65} /><span className="cf-sidebar-label">{item.label}</span></NavLink>)}</nav>
      <div className="cf-sidebar-bottom"><div className="cf-user"><Avatar name={user.data?.full_name ?? "User"} /><div className="cf-sidebar-label min-w-0 flex-1"><p className="truncate text-xs font-semibold">{user.data?.full_name ?? "Your account"}</p><p className="mt-0.5 truncate text-[11px] text-slate-400 capitalize">{membership?.role ?? "Workspace member"}</p></div><button className="cf-icon-button cf-sidebar-label" aria-label="Sign out" onClick={() => void logout()}><LogOut size={16} /></button></div>
        <button className="cf-collapse-button" onClick={() => setCollapsed((value) => { localStorage.setItem("cf-sidebar-collapsed", value ? "0" : "1"); return !value; })} aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}>{collapsed ? <PanelLeftOpen size={16} /> : <><PanelLeftClose size={16} /><span>Collapse sidebar</span></>}</button></div>
    </aside>
    <div className="cf-content"><header className="cf-topbar"><div className="flex items-center gap-2 min-w-0"><span className="cf-mobile-brand cf-logo"><Layers2 size={15} /></span><span className="truncate text-xs text-slate-400">{membership?.organization_name ?? "Workspace"}</span><span className="text-slate-300">/</span><span className="text-xs font-medium">{active?.label ?? "Details"}</span></div><div className="flex items-center gap-5"><button className="cf-topbar-search" onClick={() => setCommandOpen(true)} aria-label="Search workspace (Control or Command K)"><Search size={15} /><span>Search anything</span><kbd>Ctrl K</kbd></button><button className="cf-icon-button" aria-label="Account and workspaces" onClick={() => setAccountOpen(true)}><Avatar name={user.data?.full_name ?? "User"} /></button></div></header>
      {offline && <div className="cf-offline" role="status"><WifiOff size={14} /> You are offline. Saved records will refresh when you reconnect.</div>}
      {user.error && <div className="px-6 pt-4"><div className="cf-alert cf-alert-error">{user.error.message} <button className="underline" onClick={() => void logout()}>Sign in again</button></div></div>}
      <main id="workspace-main" key={snapshot} tabIndex={-1}><ErrorBoundary><Suspense fallback={<PageSkeleton />}><Outlet /></Suspense></ErrorBoundary></main>
    </div>
    <nav className="cf-mobile-nav" aria-label="Mobile navigation">{navItems.map(({ icon: Icon, ...item }) => <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => isActive ? "active" : ""}><Icon size={19} strokeWidth={1.6} /><span>{item.label}</span></NavLink>)}<button onClick={() => setCreating(true)} aria-label="Workspace menu" className="sr-only">Workspace</button></nav>
    {accountOpen && <Modal title="Your account" onClose={() => setAccountOpen(false)}><div className="flex gap-3 items-center mb-5"><Avatar name={user.data?.full_name ?? "User"} /><div><p className="font-medium">{user.data?.full_name}</p><p className="text-xs text-slate-400">{user.data?.email}</p></div></div><label className="cf-field"><span>Workspace</span><select className="cf-input" value={session.organization() ?? ""} onChange={(e) => { setAccountOpen(false); void switchWorkspace(e.target.value); }}>{user.data?.memberships.map((m) => <option key={m.organization_id} value={m.organization_id}>{m.organization_name}</option>)}</select></label><div className="mt-6 flex flex-wrap gap-2"><Button secondary onClick={() => { setAccountOpen(false); setCreating(true); }}><Plus size={14} />New workspace</Button><Button secondary onClick={() => void logout()}><LogOut size={14} />Sign out</Button></div></Modal>}
    {commandOpen && <CommandPalette onClose={closeCommand} />}
    {creating && <Modal title="Create a workspace" onClose={() => setCreating(false)} busy={create.isPending}><p className="text-sm text-slate-500 mb-6">A separate, private organization under your existing account.</p><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}><Field label="Organization name" required value={name} onChange={(e) => { const next = e.target.value; setName(next); if (!slug || slug === slugify(name)) setSlug(slugify(next)); }} autoFocus placeholder="Acme Advisory" /><Field label="Workspace slug" required value={slug} onChange={(e) => setSlug(slugify(e.target.value))} placeholder="acme-advisory" />{create.error && <p className="cf-alert cf-alert-error">{create.error.message}</p>}<div className="flex gap-2 pt-3"><Button type="submit" disabled={create.isPending || name.trim().length < 2 || slug.trim().length < 2}>{create.isPending ? "Creating..." : "Create workspace"}</Button><Button secondary onClick={() => setCreating(false)} disabled={create.isPending}>Cancel</Button></div></form></Modal>}
  </div>;
}
