import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test, vi } from "vitest";
import { api } from "../lib/api";
import { session } from "../lib/session";
import { PeoplePage } from "../pages/people";
import type { Person } from "../types";
vi.mock("../lib/api", () => ({ api: vi.fn() }));
vi.mock("../lib/workspace", () => ({ useWorkspace: () => ({ canWrite: true }) }));
const records: Person[] = Array.from({ length: 71 }, (_, n) => ({ id: String(n + 1), organization_id: "org-a", display_name: `Test person ${String(n + 1).padStart(3, "0")}`, first_name: "Test", last_name: String(n + 1), availability_status: "available", profile_status: "active", created_at: "2026-01-01", updated_at: "2026-01-01" }));
function mount() {
  session.set("test-token", "org-a");
  vi.mocked(api).mockResolvedValue({ items: records, total: 71, limit: 100, offset: 0 });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(<QueryClientProvider client={client}><MemoryRouter><PeoplePage /></MemoryRouter></QueryClientProvider>);
}
test("allows reaching person 71 rather than silently displaying only 50", async () => {
  mount(); await screen.findByText("Test person 001");
  fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  expect(await screen.findByText("Test person 071")).toBeInTheDocument();
  expect(screen.getByText("51 - 71 of 71")).toBeInTheDocument();
});
test("search finds a record beyond the visible first page", async () => {
  mount(); await screen.findByText("Test person 001");
  fireEvent.change(screen.getByRole("textbox", { name: "Search people" }), { target: { value: "Test person 071" } });
  expect(await screen.findByText("Test person 071")).toBeInTheDocument();
  expect(screen.queryByText("Test person 001")).not.toBeInTheDocument();
});
