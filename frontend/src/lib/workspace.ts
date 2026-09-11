import { useQuery } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import type { CurrentUser } from "../types";
import { api } from "./api";
import { qk } from "./queryKeys";
import { session } from "./session";
export function useWorkspace() {
  useSyncExternalStore(session.subscribe, session.snapshot, () => "");
  const user = useQuery({ queryKey: qk("current-user"), queryFn: ({ signal }) => api<CurrentUser>("/auth/me", { signal }), enabled: Boolean(session.token()), staleTime: 300_000 });
  const membership = user.data?.memberships.find((item) => item.organization_id === session.organization());
  const role = membership?.role ?? "viewer";
  return { user, membership, role, canWrite: ["owner", "admin", "manager", "data_entry"].includes(role), canReview: ["owner", "admin", "manager", "reviewer", "data_entry"].includes(role), canManage: ["owner", "admin", "manager"].includes(role) };
}
