import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../lib/api";
import { fetchDirectory, filterPeople } from "../lib/people";
import type { Person } from "../types";
vi.mock("../lib/api", () => ({ api: vi.fn() }));
const person = (n: number): Person => ({ id: String(n), organization_id: "org-a", first_name: "Person", last_name: String(n), display_name: `Person ${n}`, professional_title: n === 101 ? "Tax advisor" : "Engineer", country_of_residence: n === 101 ? "Kenya" : "Rwanda", availability_status: "available", profile_status: "active", created_at: "2026-01-01", updated_at: "2026-01-01" });
beforeEach(() => vi.mocked(api).mockReset());
test("loads every backend page, including the record after 100", async () => {
  vi.mocked(api).mockResolvedValueOnce({ items: Array.from({ length: 100 }, (_, i) => person(i + 1)), total: 101, limit: 100, offset: 0 }).mockResolvedValueOnce({ items: [person(101)], total: 101, limit: 100, offset: 100 });
  const people = await fetchDirectory();
  expect(people).toHaveLength(101);
  expect(people.at(-1)?.id).toBe("101");
  expect(api).toHaveBeenNthCalledWith(2, "/people?limit=100&offset=100", { signal: undefined });
});
test("passes an abort signal to each directory request", async () => {
  const controller = new AbortController();
  vi.mocked(api).mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 });
  await fetchDirectory(controller.signal);
  expect(api).toHaveBeenCalledWith("/people?limit=100&offset=0", { signal: controller.signal });
});
test("does not silently present an incomplete directory as complete", async () => {
  vi.mocked(api).mockResolvedValue({ items: [], total: 71, limit: 100, offset: 0 });
  await expect(fetchDirectory()).rejects.toThrow("directory changed");
});
test("search includes titles and locations, including later-page records", () => {
  const all = Array.from({ length: 101 }, (_, i) => person(i + 1));
  expect(filterPeople(all, "tax advisor", "", "").map((p) => p.id)).toEqual(["101"]);
  expect(filterPeople(all, "", "available", "Kenya").map((p) => p.id)).toEqual(["101"]);
});
