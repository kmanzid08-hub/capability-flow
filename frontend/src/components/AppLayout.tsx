import {
  Building2,
  ChevronsUpDown,
  Gauge,
  GitBranch,
  LogOut,
  Plus,
  Radar,
  Users,
  X,
} from "lucide-react";
import React from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  NavLink,
  Outlet,
  useNavigate,
} from "react-router-dom";

import { api } from "../lib/api";
import { session } from "../lib/session";
import type { CurrentUser } from "../types";

const navItems = [
  { to: "/", label: "Dashboard", icon: Gauge, end: true },
  { to: "/opportunities", label: "Opportunities", icon: Radar, end: false },
  { to: "/pipeline", label: "Pipeline", icon: GitBranch, end: false },
  { to: "/people", label: "People", icon: Users, end: false },
  { to: "/organization", label: "Organization", icon: Building2, end: false },
];

type WorkspaceResponse = {
  id: string;
  name: string;
  slug: string;
  status: string;
  membership_id: string;
  role: string;
};

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");
}

export function AppLayout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [creatingWorkspace, setCreatingWorkspace] = React.useState(false);
  const [workspaceName, setWorkspaceName] = React.useState("");
  const [workspaceSlug, setWorkspaceSlug] = React.useState("");
  const [workspaceError, setWorkspaceError] = React.useState<string | null>(null);

  const currentOrganizationId = session.organization();

  const userQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: () => api<CurrentUser>("/auth/me"),
    staleTime: 5 * 60 * 1000,
  });

  const organizationQuery = useQuery({
    queryKey: ["current-organization", currentOrganizationId],
    queryFn: () => api<WorkspaceResponse>("/organizations/current"),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(currentOrganizationId),
  });

  const createWorkspace = useMutation({
    mutationFn: () =>
      api<WorkspaceResponse>("/organizations", {
        method: "POST",
        body: JSON.stringify({
          name: workspaceName.trim(),
          slug: workspaceSlug.trim(),
        }),
      }),
    onSuccess: (workspace) => {
      session.setOrganization(workspace.id);
      setCreatingWorkspace(false);
      setWorkspaceName("");
      setWorkspaceSlug("");
      setWorkspaceError(null);
      queryClient.clear();
      navigate("/", { replace: true });
    },
    onError: (error) => {
      setWorkspaceError(
        error instanceof Error ? error.message : "Workspace creation failed.",
      );
    },
  });

  const switchWorkspace = (organizationId: string) => {
    if (!organizationId || organizationId === currentOrganizationId) {
      return;
    }

    session.setOrganization(organizationId);
    queryClient.clear();
    navigate("/", { replace: true });
  };

  const logout = () => {
    session.clear();
    queryClient.clear();
    navigate("/login", { replace: true });
  };

  const memberships = userQuery.data?.memberships ?? [];

  return (
    <div className="min-h-screen bg-[#f8f7f2] text-ink lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="border-b border-white/10 bg-ink text-white lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between px-6 py-5 lg:block lg:px-7 lg:py-8">
          <NavLink to="/" className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-coral font-serif text-lg">
              C
            </span>
            <span>
              <span className="block font-serif text-lg">Capability Flow</span>
              <span className="block text-[11px] uppercase tracking-[.18em] text-white/35">
                Capability intelligence
              </span>
            </span>
          </NavLink>

          <button
            type="button"
            onClick={logout}
            className="rounded-lg p-2 text-white/50 hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Sign out"
          >
            <LogOut size={18} />
          </button>
        </div>

        <div className="mx-4 mb-5 rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[.14em] text-white/35">
            <ChevronsUpDown size={13} />
            Workspace
          </div>

          {userQuery.isLoading ? (
            <p className="py-2 text-sm text-white/45">Loading…</p>
          ) : memberships.length ? (
            <select
              aria-label="Current workspace"
              value={currentOrganizationId ?? ""}
              onChange={(event) => switchWorkspace(event.target.value)}
              className="w-full rounded-lg border border-white/10 bg-ink px-3 py-2.5 text-sm font-semibold text-white outline-none"
            >
              {memberships.map((membership) => (
                <option
                  key={membership.organization_id}
                  value={membership.organization_id}
                >
                  {membership.organization_name}
                </option>
              ))}
            </select>
          ) : (
            <p className="py-2 text-sm text-white/45">No active workspace</p>
          )}

          <p className="mt-2 truncate text-xs text-white/35">
            {organizationQuery.data
              ? `${organizationQuery.data.role} · ${organizationQuery.data.slug}`
              : "Private organization workspace"}
          </p>

          <button
            type="button"
            onClick={() => {
              setWorkspaceError(null);
              setCreatingWorkspace(true);
            }}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-xs font-semibold text-white/70 hover:bg-white/15 hover:text-white"
          >
            <Plus size={14} />
            New workspace
          </button>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-4 pb-4 lg:block lg:space-y-1 lg:px-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    "flex shrink-0 items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition",
                    isActive
                      ? "bg-white text-ink"
                      : "text-white/55 hover:bg-white/10 hover:text-white",
                  ].join(" ")
                }
              >
                <Icon size={18} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 hidden p-4 lg:block">
          <button
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-white/45 hover:bg-white/10 hover:text-white"
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0">
        <Outlet />
      </main>

      {creatingWorkspace && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-5">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-serif text-2xl">Create workspace</h2>
                <p className="mt-1 text-sm leading-6 text-slate-500">
                  This creates a completely separate organization workspace under
                  your existing account.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setCreatingWorkspace(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <label className="mt-5 block text-sm font-medium text-slate-700">
              Organization name
              <input
                value={workspaceName}
                onChange={(event) => {
                  const value = event.target.value;
                  setWorkspaceName(value);

                  if (!workspaceSlug || workspaceSlug === slugify(workspaceName)) {
                    setWorkspaceSlug(slugify(value));
                  }
                }}
                className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-evergreen"
                placeholder="Acme Advisory"
              />
            </label>

            <label className="mt-4 block text-sm font-medium text-slate-700">
              Workspace slug
              <input
                value={workspaceSlug}
                onChange={(event) =>
                  setWorkspaceSlug(slugify(event.target.value))
                }
                className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-evergreen"
                placeholder="acme-advisory"
              />
            </label>

            {workspaceError && (
              <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
                {workspaceError}
              </p>
            )}

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                disabled={
                  createWorkspace.isPending ||
                  workspaceName.trim().length < 2 ||
                  workspaceSlug.trim().length < 2
                }
                onClick={() => createWorkspace.mutate()}
                className="rounded-xl bg-evergreen px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                {createWorkspace.isPending ? "Creating…" : "Create workspace"}
              </button>

              <button
                type="button"
                onClick={() => setCreatingWorkspace(false)}
                className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
