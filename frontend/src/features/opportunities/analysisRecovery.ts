import {
  ApiError,
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

const POLL_INTERVAL_MS = 3000;
const START_REASSERT_INTERVAL_MS = 15000;
const ANALYSIS_WAIT_TIMEOUT_MS = 20 * 60 * 1000;

type AnalysisStartResponse = {
  status: AnalysisStatus | "running";
  opportunity_id: string;
  target_version?: number;
  previous_version?: number;
  analysis_version?: number;
};

function sleep(delayMs: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, delayMs);
  });
}

function analysisStatusMessage(status: AnalysisStatus): string {
  switch (status) {
    case "queued":
      return "Analysis queued";
    case "fetching":
      return "Reading opportunity sources";
    case "extracting":
    case "analyzing":
      return "Analyzing requirements";
    case "matching":
      return "Matching your team";
    case "building_team":
      return "Building recommended teams";
    default:
      return "Analyzing opportunity";
  }
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
    { timeoutMs: 20000 },
  );
}

export async function analyzeOpportunityWithRecovery(
  opportunityId: string,
  onProgress?: (message: string) => void,
): Promise<OpportunityAnalysis> {
  const deadline = Date.now() + ANALYSIS_WAIT_TIMEOUT_MS;
  let targetVersion = 0;
  let nextStartReassertAt = 0;
  let lastStatus: AnalysisStatus | null = null;

  try {
    const baseline = await latestOpportunityAnalysis(opportunityId);
    targetVersion = ACTIVE_ANALYSIS_STATUSES.has(baseline.status)
      ? baseline.version
      : baseline.version + 1;
  } catch (error) {
    if (
      !(error instanceof ApiError && error.status === 404) &&
      !isOpportunityAnalysisConnectionError(error)
    ) {
      throw error;
    }
  }

  const startOrResume = async (resume: boolean): Promise<void> => {
    const resumeQuery =
      resume && targetVersion > 0
        ? `?resume_version=${targetVersion}`
        : "";

    try {
      const started = await api<AnalysisStartResponse>(
        `/opportunities/${opportunityId}/analyze/start${resumeQuery}`,
        {
          method: "POST",
          timeoutMs: 30000,
        },
      );

      const candidateVersion =
        started.target_version ??
        started.analysis_version ??
        ((started.previous_version ?? 0) + 1);

      targetVersion = Math.max(targetVersion, candidateVersion);
      nextStartReassertAt = Date.now() + START_REASSERT_INTERVAL_MS;
      onProgress?.(
        started.status === "queued"
          ? "Analysis queued"
          : "Analysis is running",
      );
    } catch (error) {
      if (!isOpportunityAnalysisConnectionError(error)) {
        throw error;
      }

      nextStartReassertAt = Date.now() + POLL_INTERVAL_MS;
      onProgress?.("Reconnecting to analysis");
    }
  };

  await startOrResume(false);

  while (Date.now() < deadline) {
    await sleep(POLL_INTERVAL_MS);

    try {
      const analysis =
        await latestOpportunityAnalysis(opportunityId);

      if (targetVersion === 0) {
        if (ACTIVE_ANALYSIS_STATUSES.has(analysis.status)) {
          targetVersion = analysis.version;
        } else if (Date.now() >= nextStartReassertAt) {
          await startOrResume(false);
          continue;
        } else {
          continue;
        }
      }

      if (analysis.version < targetVersion) {
        onProgress?.("Analysis queued");
        if (Date.now() >= nextStartReassertAt) {
          await startOrResume(true);
        }
        continue;
      }

      targetVersion = Math.max(targetVersion, analysis.version);
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
        onProgress?.(analysisStatusMessage(analysis.status));
        if (Date.now() >= nextStartReassertAt) {
          await startOrResume(true);
        }
        continue;
      }
    } catch (statusError) {
      if (
        statusError instanceof ApiError &&
        statusError.status === 404
      ) {
        if (Date.now() >= nextStartReassertAt) {
          await startOrResume(targetVersion > 0);
        }
        continue;
      }

      if (isOpportunityAnalysisConnectionError(statusError)) {
        onProgress?.("Reconnecting to analysis");
        continue;
      }

      throw statusError;
    }
  }

  if (lastStatus && ACTIVE_ANALYSIS_STATUSES.has(lastStatus)) {
    throw new Error(
      "The analysis is still running on the server. You can leave this " +
        "page and check the opportunity again shortly.",
    );
  }

  throw new Error(
    "The analysis job could not be confirmed. Your source is saved. " +
      "Please retry analysis when the service is available.",
  );
}
