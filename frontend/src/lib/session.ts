const TOKEN_KEY = "capability-flow-token";
const ORG_KEY = "capability-flow-organization";
export const session = {
  token: () => localStorage.getItem(TOKEN_KEY),
  organization: () => localStorage.getItem(ORG_KEY),
  set(token: string, organizationId: string) { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(ORG_KEY, organizationId); },
  clear() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(ORG_KEY); },
};

