import { session } from "./session";
/** Workspace isolation; a session change also clears the QueryClient in AppLayout. */
export function qk(resource: string, ...details: unknown[]) {
  return [resource, session.organization() ?? "signed-out", ...details] as const;
}
