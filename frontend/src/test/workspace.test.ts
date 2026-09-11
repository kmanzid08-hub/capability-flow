import { beforeEach, expect, test, vi } from "vitest";
import { qk } from "../lib/queryKeys";
import { session } from "../lib/session";
beforeEach(() => session.clear());
test("separates directory and overview query results", () => {
  session.set("test-token", "org-a");
  expect(qk("people", "count")).not.toEqual(qk("people", "directory"));
});
test("separates the same resource by organization", () => {
  session.set("test-token", "org-a"); const first = qk("people", "directory");
  session.setOrganization("org-b");
  expect(qk("people", "directory")).not.toEqual(first);
});
test("notifies session subscribers on workspace change and clears credentials", () => {
  const listener = vi.fn(); const stop = session.subscribe(listener);
  session.set("test-token", "org-a"); session.setOrganization("org-b"); session.clear();
  expect(listener).toHaveBeenCalledTimes(3);
  expect(session.token()).toBeNull(); expect(session.organization()).toBeNull(); stop();
});
