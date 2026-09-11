const TOKEN_KEY = "capability-flow-token";
const ORG_KEY = "capability-flow-organization";
const listeners = new Set<() => void>();
function notify() { for (const listener of listeners) listener(); }
if (typeof window !== "undefined") window.addEventListener("storage", (event) => { if (event.key === TOKEN_KEY || event.key === ORG_KEY || event.key === null) notify(); });
export const session = {
  token: () => localStorage.getItem(TOKEN_KEY),
  organization: () => localStorage.getItem(ORG_KEY),
  snapshot: () => `${localStorage.getItem(TOKEN_KEY) ?? ""}|${localStorage.getItem(ORG_KEY) ?? ""}`,
  subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
  set(token: string, organizationId: string) { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(ORG_KEY, organizationId); notify(); },
  setToken(token: string) { localStorage.setItem(TOKEN_KEY, token); notify(); },
  setOrganization(organizationId: string) { localStorage.setItem(ORG_KEY, organizationId); notify(); },
  clearOrganization() { localStorage.removeItem(ORG_KEY); notify(); },
  clear() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(ORG_KEY); notify(); },
};
