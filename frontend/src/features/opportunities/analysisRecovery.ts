import { ApiError, api } from "../../lib/api";
import type { AnalysisStatus, OpportunityAnalysis } from "../../types";

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

export function isOpportunityAnalysisConnectionError(error: unknown): boolean {
  if (error instanceof ApiError && error.status === 0) {
    return true;
  }
  const message = error instanceof Error ? error.message.toLowerCase() : "";
  return (
    message.includes("failed to fetch") ||
    message.includes("network") ||
    message.includes("load failed") ||
    message.includes("timed out") ||
    message.includes("unable to reach") ||
    message.includes("cannot reach the server")
  );
}

async function latestOpportunityAnalysis(
  opportunityId: string,
): Promise<OpportunityAnalysis> {
  return api<OpportunityAnalysis>(`/opportunities/${opportunityId}/analysis`, {
    timeoutMs: 20000,
  });
}

export async function analyzeOpportunityWithRecovery(
  opportunityId: string,
  onProgress?: (message: string) => void,
): Promise<OpportunityAnalysis> {
  const deadline = Date.now() + ANALYSIS_WAIT_TIMEOUT_MS;
  let baselineVersion = 0;
  let targetVersion = 0;
  let baselineWasActive = false;
  let startConfirmed = false;
  let sawTargetActivity = false;
  let lastStatus: AnalysisStatus | null = null;

  try {
    const baseline = await latestOpportunityAnalysis(opportunityId);
    baselineVersion = baseline.version;
    baselineWasActive = ACTIVE_ANALYSIS_STATUSES.has(baseline.status);
    targetVersion = baselineWasActive ? baseline.version : baseline.version + 1;
    if (baselineWasActive) {
      sawTargetActivity = true;
      onProgress?.(analysisStatusMessage(baseline.status));
    }
  } catch (error) {
    if (
      !(error instanceof ApiError && error.status === 404) &&
      !isOpportunityAnalysisConnectionError(error)
    ) {
      throw error;
    }
  }

  // A user action may create at most one start request. Durable server-side jobs
  // recover from worker restarts; the browser must not re-enqueue the same work
  // every few seconds while it is polling.
  if (!baselineWasActive) {
    try {
      const started = await api<AnalysisStartResponse>(
        `/opportunities/${opportunityId}/analyze/start`,
        {
          method: "POST",
          timeoutMs: 30000,
        },
      );
      const candidateVersion =
        started.target_version ??
        started.analysis_version ??
        ((started.previous_version ?? baselineVersion) + 1);
      targetVersion = Math.max(targetVersion, candidateVersion);
      startConfirmed = true;
      onProgress?.(
        started.status === "queued" ? "Analysis queued" : "Analysis is running",
      );
    } catch (error) {
      if (!isOpportunityAnalysisConnectionError(error)) {
        throw error;
      }
      // The POST may have reached the server even when the response was lost.
      // Poll to discover the durable job rather than issuing duplicate POSTs.
      onProgress?.("Reconnecting to analysis");
    }
  }

  while (Date.now() < deadline) {
    await sleep(POLL_INTERVAL_MS);
    try {
      const analysis = await latestOpportunityAnalysis(opportunityId);
      lastStatus = analysis.status;

      if (ACTIVE_ANALYSIS_STATUSES.has(analysis.status)) {
        if (
          targetVersion === 0 ||
          analysis.version >= targetVersion ||
          analysis.version > baselineVersion
        ) {
          targetVersion = Math.max(targetVersion, analysis.version);
          sawTargetActivity = true;
        }
        onProgress?.(analysisStatusMessage(analysis.status));
        continue;
      }

      if (targetVersion > 0 && analysis.version < targetVersion) {
        onProgress?.("Analysis queued");
        continue;
      }

      const belongsToThisRun =
        startConfirmed ||
        sawTargetActivity ||
        analysis.version > baselineVersion;

      if (
        belongsToThisRun &&
        COMPLETED_ANALYSIS_STATUSES.has(analysis.status)
      ) {
        return analysis;
      }

      if (belongsToThisRun && analysis.status === "failed") {
        throw new Error(
          analysis.error_message || "Opportunity analysis failed. Please retry.",
        );
      }
    } catch (statusError) {
      if (statusError instanceof ApiError && statusError.status === 404) {
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
      "The analysis is still running on the server. You can leave this page and check the opportunity again shortly.",
    );
  }

  throw new Error(
    "The analysis job could not be confirmed. Your source is saved. Please retry once the service is available.",
  );
}
