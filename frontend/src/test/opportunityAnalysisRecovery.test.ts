import { describe, expect, it } from "vitest";

import {
  isOpportunityAnalysisConnectionError,
} from "../features/opportunities/analysisRecovery";
import { ApiError } from "../lib/api";

describe("opportunity analysis connection recovery", () => {
  it("recognizes network-level API failures", () => {
    expect(
      isOpportunityAnalysisConnectionError(
        new ApiError(0, "Failed to fetch"),
      ),
    ).toBe(true);
  });

  it("does not hide normal HTTP errors", () => {
    expect(
      isOpportunityAnalysisConnectionError(
        new ApiError(503, "AI providers are unavailable"),
      ),
    ).toBe(false);
  });
});
