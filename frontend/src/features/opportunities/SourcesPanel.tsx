import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Download,
  Trash2
} from "lucide-react";
import { useState } from "react";
import { useWorkspace } from "../../lib/workspace";

import {
  api,
  apiDownload
} from "../../lib/api";


import { StatusBadge } from "../../components/StatusBadge";
import { qk } from "../../lib/queryKeys";
import { EmptyState } from "./display";
import type { OpportunitySource } from "./shared";
import { formatDate } from "./shared";
export function SourcesPanel({
  opportunityId,
}: {
  opportunityId: string;
}) {
  const { canWrite } = useWorkspace();
  const queryClient = useQueryClient();
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: qk("opportunity-sources", opportunityId),
    queryFn: () =>
      api<OpportunitySource[]>(
        `/opportunities/${opportunityId}/sources`,
      ),
  });

  const remove = useMutation({
    mutationFn: (sourceId: string) =>
      api<void>(
        `/opportunities/${opportunityId}/sources/${sourceId}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: qk("opportunity-sources", opportunityId),
      });
    },
  });

  if (query.isLoading) {
    return (
      <p className="rounded-2xl bg-white p-5 text-sm text-slate-500">
        Loading captured sources…
      </p>
    );
  }

  if (query.error) {
    return (
      <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
        {query.error.message}
      </p>
    );
  }

  if (!query.data?.length) {
    return (
      <EmptyState
        title="No sources yet"
        text="Add the original URL or pasted client requirement."
      />
    );
  }

  return (
    <div className="grid gap-3">
      {(remove.error || downloadError) && <p role="alert" className="cf-alert cf-alert-error">{remove.error?.message ?? downloadError}</p>}
      {query.data.map((source) => (
        <article
          key={source.id}
          className="rounded-2xl border border-slate-200 bg-white p-5"
        >
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge value={source.source_type} />
                {source.file_size != null && (
                  <span className="text-xs text-slate-400">
                    {(source.file_size / 1024).toFixed(1)} KB
                  </span>
                )}
              </div>
              <p className="mt-3 truncate font-semibold">
                {source.original_filename ||
                  source.source_url ||
                  "Pasted requirement text"}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Captured {formatDate(source.created_at)}
              </p>
            </div>

            <div className="flex shrink-0 gap-2">
              {source.stored_filename && (
                <button
                  type="button"
                  onClick={() =>
                    void apiDownload(
                      `/opportunities/${opportunityId}/sources/${source.id}/download`,
                      source.original_filename || "opportunity-source",
                    ).catch((error: unknown) => setDownloadError(error instanceof Error ? error.message : "Download failed."))
                  }
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold hover:bg-slate-50"
                >
                  <Download size={15} />
                  Snapshot
                </button>
              )}
              <button
                type="button"
                disabled={remove.isPending || !canWrite}
                onClick={() => {
                  if (window.confirm("Delete this captured source?") && canWrite ) {
                     remove.mutate(source.id);
                  }
                }}
                className="rounded-xl border border-slate-200 p-2.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                aria-label="Delete source"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
