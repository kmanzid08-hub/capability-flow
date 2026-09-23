import {
  ApiError,
  OPPORTUNITY_ANALYSIS_TIMEOUT_MS,
  api,
} from "../../lib/api";
import type {
  AnalysisStatus,
  OpportunityAnalysis,
} from "../../types";

const ACTIVE_ANALYSIS_STATUSES = new Set<AnalysisStatus>([
  "queued",
  "fetching",
  "extracting",
  "analyzing",
  "matching",
  "building_team",
]);

const COMPLETED_ANALYSIS_STATUSES = new Set<AnalysisStatus>([
  "complete",
  "needs_review",
]);

const RECOVERY_DELAYS_MS = [1500, 2500, 4000, 6000, 8000, 10000];

function sleep(delayMs: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, delayMs);
  });
}

export function isOpportunityAnalysisConnectionError(
  error: unknown,
): boolean {
  if (error instanceof ApiError && error.status === 0) {
    return true;
  }

  const message =
    error instanceof Error ? error.message.toLowerCase() : "";

  return (
    message.includes("failed to fetch") ||
    message.includes("network") ||
    message.includes("load failed") ||
    message.includes("timed out") ||
    message.includes("unable to reach")
  );
}

async function latestOpportunityAnalysis(
  opportunityId: string,
): Promise<OpportunityAnalysis> {
  return api<OpportunityAnalysis>(
    `/opportunities/${opportunityId}/analysis`,
    { timeoutMs: 10000 },
  );
}

export async function analyzeOpportunityWithRecovery(
  opportunityId: string,
): Promise<OpportunityAnalysis> {
  try {
    return await api<OpportunityAnalysis>(
      `/opportunities/${opportunityId}/analyze`,
      {
        method: "POST",
        timeoutMs: OPPORTUNITY_ANALYSIS_TIMEOUT_MS,
      },
    );
  } catch (error) {
    if (!isOpportunityAnalysisConnectionError(error)) {
      throw error;
    }

    let lastStatus: AnalysisStatus | null = null;

    for (const delayMs of RECOVERY_DELAYS_MS) {
      await sleep(delayMs);

      try {
        const analysis =
          await latestOpportunityAnalysis(opportunityId);

        lastStatus = analysis.status;

        if (COMPLETED_ANALYSIS_STATUSES.has(analysis.status)) {
          return analysis;
        }

        if (analysis.status === "failed") {
          throw new Error(
            analysis.error_message ||
              "Opportunity analysis failed. Please retry.",
          );
        }

        if (ACTIVE_ANALYSIS_STATUSES.has(analysis.status)) {
          continue;
        }
      } catch (statusError) {
        if (
          statusError instanceof ApiError &&
          statusError.status === 404
        ) {
          continue;
        }

        if (isOpportunityAnalysisConnectionError(statusError)) {
          continue;
        }

        throw statusError;
      }
    }

    if (lastStatus && ACTIVE_ANALYSIS_STATUSES.has(lastStatus)) {
      throw new Error(
        "The connection was interrupted while the tender was still being " +
          "processed. The tender source is saved. Refresh the opportunity " +
          "and use Retry analysis once. Do not upload the tender again.",
      );
    }

    throw new Error(
      "The analysis connection was interrupted. The tender source is saved. " +
        "Refresh the opportunity and retry the analysis once the service is available.",
    );
  }
}
