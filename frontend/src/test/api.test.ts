import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../lib/api";
import { session } from "../lib/session";
beforeEach(() => session.set("test-token", "org-a"));
test("uses the authenticated workspace headers", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock); expect(await api("/people")).toEqual({ ok: true });
  const init = fetchMock.mock.calls[0][1] as RequestInit;
  const headers = new Headers(init.headers);
  expect(headers.get("Authorization")).toBe("Bearer test-token");
  expect(headers.get("X-Organization-ID")).toBe("org-a");
});
test("supports successful empty responses", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
  expect(await api("/people/a", { method: "DELETE" })).toBeUndefined();
});
test("preserves a useful backend error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Write access is required" }), { status: 403 })));
  await expect(api("/people")).rejects.toThrow("Write access is required");
});
test("discards an old workspace response after switching organizations", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => {
    session.setOrganization("org-b"); return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }));
  await expect(api("/people")).rejects.toThrow("workspace changed");
});
function pendingFetch(_input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return new Promise((_resolve, reject) => init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true }));
}
test("distinguishes caller cancellation from a timeout", async () => {
  vi.stubGlobal("fetch", vi.fn(pendingFetch)); const controller = new AbortController();
  const result = api("/people/a/documents/b/analyze", { method: "POST", signal: controller.signal });
  controller.abort(); await expect(result).rejects.toThrow("aborted by user");
});
test("retains timeout protection when a caller signal is supplied", async () => {
  vi.useFakeTimers(); vi.stubGlobal("fetch", vi.fn(pendingFetch));
  const controller = new AbortController();
  const result = api("/people", { timeoutMs: 100, signal: controller.signal });
  const assertion = expect(result).rejects.toThrow("timed out");
  await vi.advanceTimersByTimeAsync(101); await assertion; expect(controller.signal.aborted).toBe(false);
});
