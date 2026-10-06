import { afterEach, expect, test, vi } from "vitest";

import { analyzeOpportunityWithRecovery } from "../features/opportunities/analysisRecovery";
import { api } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: vi.fn(),
  };
});

const apiMock = vi.mocked(api);

afterEach(() => {
  apiMock.mockReset();
  vi.useRealTimers();
});

test("one re-analysis action sends only one start request while polling", async () => {
  vi.useFakeTimers();
  let analysisReads = 0;

  apiMock.mockImplementation(
    (async (path: string) => {
      if (path.endsWith("/analysis")) {
        analysisReads += 1;
        if (analysisReads === 1) {
          return { version: 3, status: "failed" };
        }
        if (analysisReads <= 3) {
          return { version: 4, status: "analyzing" };
        }
        return { version: 4, status: "complete" };
      }
      if (path.endsWith("/analyze/start")) {
        return {
          status: "queued",
          opportunity_id: "opportunity-1",
          target_version: 4,
        };
      }
      throw new Error(`Unexpected API path: ${path}`);
    }) as typeof api,
  );

  const resultPromise = analyzeOpportunityWithRecovery("opportunity-1");
  await vi.advanceTimersByTimeAsync(9_000);
  const result = await resultPromise;

  const startCalls = apiMock.mock.calls.filter(([path]) =>
    String(path).endsWith("/analyze/start"),
  );
  expect(startCalls).toHaveLength(1);
  expect(result.status).toBe("complete");
  expect(result.version).toBe(4);
});

test("an already active durable analysis is only polled", async () => {
  vi.useFakeTimers();
  let analysisReads = 0;

  apiMock.mockImplementation(
    (async (path: string) => {
      if (!path.endsWith("/analysis")) {
        throw new Error(`Unexpected API path: ${path}`);
      }
      analysisReads += 1;
      if (analysisReads === 1) {
        return { version: 7, status: "matching" };
      }
      return { version: 7, status: "complete" };
    }) as typeof api,
  );

  const resultPromise = analyzeOpportunityWithRecovery("opportunity-2");
  await vi.advanceTimersByTimeAsync(3_000);
  const result = await resultPromise;

  const startCalls = apiMock.mock.calls.filter(([path]) =>
    String(path).endsWith("/analyze/start"),
  );
  expect(startCalls).toHaveLength(0);
  expect(result.status).toBe("complete");
  expect(result.version).toBe(7);
});
