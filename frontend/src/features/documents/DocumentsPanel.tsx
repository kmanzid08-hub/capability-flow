import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Check,
  Download,
  Eye,
  FileText,
  Search,
  Sparkles,
  Square,
  Trash2,
  Upload,
  X
} from "lucide-react";
import React from "react";
import { session } from "../../lib/session";

import {
  Button,
  Field
} from "../../components/ui";
import {
  AI_ANALYSIS_TIMEOUT_MS,
  api,
  apiBlob,
  apiDownload
} from "../../lib/api";
import type {
  DocumentType,
  PersonDocument,
  ProfileSuggestion
} from "../../types";


import { EmptyCapability } from "../../components/EmptyCapability";
import { StatusBadge } from "../../components/StatusBadge";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { apiUpload } from "../../lib/api";
import { qk } from "../../lib/queryKeys";
import { useWorkspace } from "../../lib/workspace";
import { SuggestionCard } from "./SuggestionCard";
import { documentTypeOptions, normalizeSuggestionPayload, validateDocumentSelection } from "./suggestions";
import { UploadZone } from "./UploadZone";
export function DocumentsPanel({ personId, view = "documents" }: { personId: string; view?: "documents" | "review"; }) {
  const { canWrite, canReview } = useWorkspace();
  const [uploadPercent, setUploadPercent] = React.useState(0);
  const [reviewFilter, setReviewFilter] = React.useState("");
  const [reviewSearch, setReviewSearch] = React.useState("");
  const [reviewPage, setReviewPage] = React.useState(1);
  const [documentSearch, setDocumentSearch] = React.useState("");
  const [expanded, setExpanded] = React.useState<string | null>(null);
  const abortPromise = React.useRef<Promise<void> | null>(null);
  const queryClient = useQueryClient();
  const [files, setFiles] = React.useState<File[]>([]);
  const [batchProgress, setBatchProgress] = React.useState<string | null>(null);
  const [batchError, setBatchError] = React.useState<string | null>(null);
  const [documentType, setDocumentType] = React.useState<DocumentType>("cv");
  const [title, setTitle] = React.useState("");
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editPayload, setEditPayload] = React.useState<Record<string, unknown>>({});
  const [reviewNotes, setReviewNotes] = React.useState<Record<string, string>>({});
  const [preview, setPreview] = React.useState<{
    document: PersonDocument;
    kind: "pdf" | "image" | "text";
    objectUrl?: string;
    text?: string;
  } | null>(null);
  const [previewBusy, setPreviewBusy] = React.useState(false);
  const [previewError, setPreviewError] = React.useState<string | null>(null);
  const [analysisMode, setAnalysisMode] = React.useState<"single" | "all" | null>(null);
  const [analysisAborting, setAnalysisAborting] = React.useState(false);
  const [analysisNotice, setAnalysisNotice] = React.useState<string | null>(null);
  const analysisAbortController = React.useRef<AbortController | null>(null);
  const analysisAbortRequested = React.useRef(false);

  React.useEffect(() => {
    const workspace = session.snapshot();
    return () => {
      const controller = analysisAbortController.current;
      if (controller && !controller.signal.aborted) {
        analysisAbortRequested.current = true;
        controller.abort();
        if (session.snapshot() === workspace) {
          void api(`/people/${personId}/analysis/abort`, { method: "POST", timeoutMs: 10000 }).catch(() => undefined);
        }
      }
    };
  }, [personId]);

  const documents = useQuery({
    queryKey: qk("documents", personId),
    queryFn: ({ signal }) => api<PersonDocument[]>(`/people/${personId}/documents`, { signal }),
    refetchInterval: (query) => query.state.data?.some((doc) => doc.analysis_status === "processing") ? 5000 : false,
  });
  const suggestions = useQuery({
    queryKey: qk("profile-suggestions", personId),
    queryFn: () =>
      api<ProfileSuggestion[]>(`/people/${personId}/ai-suggestions?status=pending`),
  });
  const refreshProfile = (all = false) => {
    const keys = all ? ["documents", "profile-suggestions", "profile-completeness", "person", "skills", "education", "certifications", "employment", "projects"] : ["documents", "profile-suggestions", "profile-completeness"];
    for (const key of keys) void queryClient.invalidateQueries({ queryKey: qk(key, personId) });
    if (all) void queryClient.invalidateQueries({ queryKey: qk("people") });
  };

  const beginAnalysis = (mode: "single" | "all") => {
    const controller = new AbortController();
    analysisAbortController.current = controller;
    analysisAbortRequested.current = false;
    setAnalysisMode(mode);
    setAnalysisAborting(false);
    setAnalysisNotice(null);
    setBatchError(null);
    return controller;
  };

  const finishAnalysis = async (controller: AbortController) => {
    if (analysisAbortRequested.current && abortPromise.current) await abortPromise.current;
    if (analysisAbortController.current === controller) {
      analysisAbortController.current = null;
      setAnalysisMode(null);
      setAnalysisAborting(false);
    }
  };

  const abortAnalysis = async () => {
    if (!analysisMode || analysisAborting) return;
    analysisAbortRequested.current = true;
    setAnalysisAborting(true);
    setAnalysisNotice("Stopping the queue and requesting server cancellation...");
    abortPromise.current = api<{ aborted: boolean; requests_cancelled: number; }>(
      `/people/${personId}/analysis/abort`, { method: "POST", timeoutMs: 10000 },
    ).then((result) => {
      if (!result.aborted) setBatchError("The queue stopped. This server did not find an active analysis to cancel. Refresh document status before retrying.");
      setAnalysisNotice("The queue stopped. Results saved before cancellation are retained.");
    })
      .catch(() => { setBatchError("The queue stopped, but server cancellation could not be confirmed. Refresh the document status before retrying."); })
      .finally(() => { refreshProfile(); });
    analysisAbortController.current?.abort();
    await abortPromise.current;
  };

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!files.length) throw new Error("Choose one or more documents first.");
      setUploadError(null);
      setUploadPercent(0);
      const uploaded: PersonDocument[] = [];
      for (let index = 0; index < files.length; index += 1) {
        const selectedFile = files[index];
        setBatchProgress(`Uploading ${index + 1} of ${files.length}: ${selectedFile.name}`);
        const form = new FormData();
        form.append("file", selectedFile);
        form.append("document_type", documentType);
        if (title.trim() && files.length === 1) form.append("title", title.trim());
        setUploadPercent(0);
        uploaded.push(await apiUpload<PersonDocument>(`/people/${personId}/documents`, form, setUploadPercent));
        setFiles((current) => current.filter((item) => item !== selectedFile));
      }
      return uploaded;
    },
    onSuccess: () => {
      setFiles([]);
      setTitle("");
      setBatchProgress(null);
      refreshProfile();
    },
    onError: (error) => {
      setBatchProgress(null);
      setUploadError(error instanceof Error ? error.message : "Upload failed.");
      refreshProfile();
    },
  });

  const analyze = useMutation({
    mutationFn: async (documentId: string) => {
      const controller = beginAnalysis("single");
      const document = documents.data?.find((item) => item.id === documentId);
      setBatchProgress(`Analyzing: ${document?.title ?? "document"}`);
      try {
        await api(`/people/${personId}/documents/${documentId}/analyze`, {
          method: "POST",
          timeoutMs: AI_ANALYSIS_TIMEOUT_MS,
          signal: controller.signal,
        });
        return { aborted: false };
      } catch (error) {
        if (controller.signal.aborted) {
          return { aborted: true };
        }
        throw error;
      } finally {
        await finishAnalysis(controller);
      }
    },
    onSuccess: (result) => {
      setBatchProgress(null);
      if (result.aborted) {
        setAnalysisNotice("Analysis aborted. No remaining analysis will be started.");
      }
      refreshProfile();
    },
    onError: (error) => {
      setBatchProgress(null);
      setBatchError(error instanceof Error ? error.message : "Analysis failed.");
      refreshProfile();
    },
  });

  const analyzeAll = useMutation({
    mutationFn: async () => {
      const items = (documents.data ?? []).filter((item) => item.analysis_status !== "processing");
      if (!items.length) throw new Error("No idle documents are available. Wait for running analyses to finish, or upload a document.");
      const controller = beginAnalysis("all");
      const failures: string[] = [];
      let processed = 0;
      try {
        for (let index = 0; index < items.length; index += 1) {
          if (controller.signal.aborted) return { aborted: true, processed, total: items.length };
          const document = items[index];
          setBatchProgress(`Analyzing ${index + 1} of ${items.length}: ${document.title}`);
          try {
            await api(`/people/${personId}/documents/${document.id}/analyze`, {
              method: "POST", timeoutMs: AI_ANALYSIS_TIMEOUT_MS, signal: controller.signal,
            });
            processed += 1;
          } catch (error) {
            if (controller.signal.aborted) return { aborted: true, processed, total: items.length };
            const message = error instanceof Error ? error.message : "Analysis failed";
            // A lost response does not prove that the server stopped. Do not duplicate AI jobs.
            if (/failed to fetch|network|load failed|timed out/i.test(message)) {
              throw new Error(`The connection was interrupted after ${processed} successful analyses. The queue stopped. Refresh document status before retrying. ${message}`);
            }
            failures.push(`${document.title}: ${message}`);
          }
          refreshProfile();
        }
        if (failures.length) throw new Error(`${processed} of ${items.length} documents completed. ${failures.join(" | ")}`);
        return { aborted: false, processed, total: items.length };
      } finally { await finishAnalysis(controller); }
    },
    onSuccess: (result) => {
      setBatchProgress(null);
      setAnalysisNotice(result.aborted
        ? `Analysis stopped. ${result.processed} of ${result.total} documents completed successfully. Saved results are retained; unfinished documents can be retried.`
        : `Analysis finished. ${result.processed} documents completed.`);
      refreshProfile();
    },
    onError: (error) => {
      setBatchProgress(null);
      setBatchError(error instanceof Error ? error.message : "Some documents could not be analyzed.");
      refreshProfile();
    },
  });

  const accept = useMutation({
    mutationFn: async (suggestion: ProfileSuggestion) => {
      const note = reviewNotes[suggestion.id]?.trim();
      if (note) {
        await api(`/people/${personId}/ai-suggestions/${suggestion.id}`, {
          method: "PATCH",
          body: JSON.stringify({ review_note: note }),
        });
      }
      return api(`/people/${personId}/ai-suggestions/${suggestion.id}/accept`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      setEditingId(null);
      refreshProfile(true);
    },
  });

  const acceptAll = useMutation({
    mutationFn: async () => {
      const pending = suggestions.data ?? [];
      if (!pending.length) {
        return { total: 0, accepted: 0, failed: 0, failures: [] as Array<{ title: string; detail: string; }> };
      }

      setBatchError(null);
      setBatchProgress(`Accepting ${pending.length} AI suggestions…`);

      // Save any reviewer notes first. A note failure should not prevent the
      // remaining suggestions from being accepted.
      for (const suggestion of pending) {
        const note = reviewNotes[suggestion.id]?.trim();
        if (!note) continue;
        try {
          await api(`/people/${personId}/ai-suggestions/${suggestion.id}`, {
            method: "PATCH",
            body: JSON.stringify({ review_note: note }),
          });
        } catch {
          // The backend accept-all endpoint is deliberately resilient and will
          // continue with every other valid suggestion.
        }
      }

      return api<{
        total: number;
        accepted: number;
        failed: number;
        failures: Array<{ suggestion_id: string; title: string; detail: string; }>;
      }>(`/people/${personId}/ai-suggestions/accept-all`, {
        method: "POST",
      });
    },
    onSuccess: (result) => {
      setBatchProgress(null);
      setEditingId(null);
      if (result.failed > 0) {
        const examples = result.failures
          .slice(0, 3)
          .map((item) => `${item.title}: ${item.detail}`)
          .join(" | ");
        setBatchError(
          `${result.accepted} of ${result.total} suggestions were saved. ` +
          `${result.failed} still need review.${examples ? ` ${examples}` : ""}`,
        );
      } else {
        setBatchError(null);
      }
      refreshProfile(true);
    },
    onError: (error) => {
      setBatchProgress(null);
      setBatchError(error instanceof Error ? error.message : "Accept all failed.");
      refreshProfile(true);
    },
  });

  const reject = useMutation({
    mutationFn: async (suggestion: ProfileSuggestion) => {
      const note = reviewNotes[suggestion.id]?.trim();
      if (note) {
        await api(`/people/${personId}/ai-suggestions/${suggestion.id}`, {
          method: "PATCH",
          body: JSON.stringify({ review_note: note }),
        });
      }
      return api(`/people/${personId}/ai-suggestions/${suggestion.id}/reject`, {
        method: "POST",
      });
    },
    onSuccess: () => refreshProfile(),
  });

  const acceptEdited = useMutation({
    mutationFn: async (suggestion: ProfileSuggestion) => {
      const payload = normalizeSuggestionPayload(suggestion.category, editPayload);
      const reviewNote = reviewNotes[suggestion.id]?.trim() || null;

      await api(`/people/${personId}/ai-suggestions/${suggestion.id}`, {
        method: "PATCH",
        body: JSON.stringify({ payload, review_note: reviewNote }),
      });

      return api(`/people/${personId}/ai-suggestions/${suggestion.id}/accept`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      setEditingId(null);
      setEditPayload({});
      refreshProfile(true);
    },
  });

  const remove = useMutation({
    mutationFn: (documentId: string) =>
      api<void>(`/people/${personId}/documents/${documentId}`, { method: "DELETE" }),
    onSuccess: () => refreshProfile(),
  });

  const pendingCount = suggestions.data?.length ?? 0;
  const documentById = new Map((documents.data ?? []).map((item) => [item.id, item]));
  const reviewBusy = !canReview || analysisMode !== null || accept.isPending || reject.isPending || acceptEdited.isPending || acceptAll.isPending;

  const closePreview = () => {
    if (preview?.objectUrl) {
      window.URL.revokeObjectURL(preview.objectUrl);
    }
    setPreview(null);
    setPreviewError(null);
  };

  const openPreview = async (document: PersonDocument) => {
    closePreview();
    setPreviewBusy(true);
    setPreviewError(null);
    const extension = document.file_extension.toLowerCase();
    const nativePreview =
      extension === ".pdf" ||
      [".jpg", ".jpeg", ".png", ".webp", ".gif"].includes(extension);

    try {
      if (nativePreview) {
        const blob = await apiBlob(
          `/people/${personId}/documents/${document.id}/view`,
        );
        const objectUrl = window.URL.createObjectURL(blob);
        setPreview({
          document,
          kind: extension === ".pdf" ? "pdf" : "image",
          objectUrl,
        });
      } else {
        const result = await api<{ text: string; }>(
          `/people/${personId}/documents/${document.id}/preview-text`,
        );
        setPreview({ document, kind: "text", text: result.text });
      }
    } catch (error) {
      setPreviewError(
        error instanceof Error ? error.message : "Document preview failed.",
      );
    } finally {
      setPreviewBusy(false);
    }
  };

  const startEditing = (suggestion: ProfileSuggestion) => {
    setEditingId(suggestion.id);
    setExpanded(suggestion.id);
    const payload = { ...suggestion.payload };
    if (suggestion.category === "education") {
      if (payload.start_date == null && payload.start_year != null) {
        payload.start_date = String(payload.start_year);
      }
      if (payload.graduation_date == null && payload.graduation_year != null) {
        payload.graduation_date = String(payload.graduation_year);
      }
      delete payload.start_year;
      delete payload.graduation_year;
    }
    setEditPayload(payload);
  };

  const updateEditValue = (key: string, value: unknown) => {
    setEditPayload((current) => ({ ...current, [key]: value }));
  };

  React.useEffect(() => {
    const objectUrl = preview?.objectUrl;
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [preview?.objectUrl]);
  const visibleDocuments = (documents.data ?? []).filter((doc) => `${doc.title} ${doc.original_filename}`.toLowerCase().includes(documentSearch.toLowerCase()));
  const filteredSuggestions = (suggestions.data ?? []).filter((item) => (!reviewFilter || item.category === reviewFilter) && `${item.title} ${documentById.get(item.source_document_id)?.title ?? ""}`.toLowerCase().includes(reviewSearch.toLowerCase()));
  const currentReviewPage = Math.min(reviewPage, Math.max(1, Math.ceil(filteredSuggestions.length / 20)));
  const visibleSuggestions = filteredSuggestions.slice((currentReviewPage - 1) * 20, currentReviewPage * 20);
  const selectFiles = (selected: File[]) => {
    const invalid = selected.map(validateDocumentSelection).find(Boolean);
    if (invalid) { setUploadError(invalid); return; }
    setUploadError(null);
    setFiles(selected);
  };

  return <div className="space-y-5">
    {(analysisMode || analysisNotice) && <div className="cf-progress" role="status"><div><p className="font-medium">{analysisMode ? batchProgress ?? "Analyzing documents..." : analysisNotice}</p>{analysisMode && <p className="mt-1 text-xs text-slate-400">Working with your configured AI providers. Large files can take several minutes.</p>}</div>{analysisMode && <Button danger disabled={analysisAborting} onClick={() => void abortAnalysis()}><Square size={13} />{analysisAborting ? "Stopping..." : "Abort analysis"}</Button>}</div>}
    {view === "documents" && <>
      {canWrite && <details className="cf-panel" open={files.length > 0 || !documents.data?.length || undefined}><summary className="flex items-center justify-between gap-3 cursor-pointer list-none"><div><h2 className="text-base font-semibold">Add evidence</h2><p className="mt-1 text-xs text-slate-400">CVs, qualifications, and supporting documents. Up to 250 MB per file.</p></div><Upload size={18} className="text-slate-400" /></summary><div className="mt-5"><UploadZone disabled={uploadMutation.isPending || analysisMode !== null} onFiles={selectFiles} /><div className="grid sm:grid-cols-2 gap-4 mt-5"><label className="cf-field"><span>Document type</span><select className="cf-input" value={documentType} onChange={(event) => setDocumentType(event.target.value as DocumentType)}>{documentTypeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><Field label="Title (optional)" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Use the filename" /></div>{files.length > 0 && <div className="mt-4 space-y-2">{files.map((file, index) => <div key={`${file.name}-${index}`} className="flex items-center justify-between gap-4 text-xs rounded-lg bg-slate-50 px-3 py-2"><span className="truncate">{file.name}<span className="text-slate-400 ml-3">{(file.size / (1024 * 1024)).toFixed(1)} MB</span></span><button className="cf-icon-button" aria-label={`Remove ${file.name} from selection`} disabled={uploadMutation.isPending} onClick={() => setFiles((current) => current.filter((_, i) => i !== index))}><X size={13} /></button></div>)}</div>}{uploadMutation.isPending && <div className="mt-4" role="status"><p className="text-xs text-slate-500">{batchProgress}</p><progress className="w-full h-1 mt-2 accent-slate-700" max={100} value={uploadPercent} aria-label="Upload progress" /><p className="text-xs text-slate-400 mt-1">{uploadPercent === 100 ? "File transmitted. Waiting for the server to finish saving..." : `${uploadPercent}% transmitted`}</p></div>}{(uploadError || uploadMutation.error) && <p role="alert" className="cf-alert cf-alert-error mt-4">{uploadError ?? uploadMutation.error?.message}</p>}<div className="mt-5 flex gap-2"><Button disabled={!files.length || uploadMutation.isPending || analysisMode !== null} onClick={() => uploadMutation.mutate()}><Upload size={14} />{uploadMutation.isPending ? "Uploading..." : `Upload ${files.length > 1 ? `${files.length} documents` : "document"}`}</Button>{files.length > 0 && <Button secondary disabled={uploadMutation.isPending} onClick={() => setFiles([])}>Clear selection</Button>}</div></div></details>}
      <section className="cf-panel"><div className="cf-panel-heading"><div><h2>Evidence library <span className="text-slate-400 font-normal ml-1">{documents.data?.length ?? ""}</span></h2><p className="text-xs text-slate-400 mt-1">Original documents stay linked to the profile.</p></div>{canWrite && !analysisMode && <Button disabled={!documents.data?.length || uploadMutation.isPending || acceptAll.isPending} onClick={() => analyzeAll.mutate()}><Sparkles size={14} />Analyze all</Button>}</div><label className="cf-search mb-4 w-full"><Search size={15} /><input value={documentSearch} onChange={(event) => setDocumentSearch(event.target.value)} placeholder="Find a document..." aria-label="Search documents" /></label>{documents.isLoading ? <Skeleton rows={3} /> : documents.error ? <p className="cf-alert cf-alert-error">{documents.error.message}</p> : visibleDocuments.length ? <div className="divide-y divide-slate-100">{visibleDocuments.map((document) => <article className="py-4" key={document.id}><div className="flex flex-col xl:flex-row justify-between gap-4"><div className="flex gap-3 min-w-0"><div className="cf-empty-icon m-0 w-10 h-11 shrink-0"><FileText size={18} /></div><div className="min-w-0"><h3 className="text-sm font-medium break-words">{document.title}</h3><p className="text-[11px] text-slate-400 mt-1 break-all">{document.original_filename} / {(document.file_size / (1024 * 1024)).toFixed(1)} MB</p><div className="mt-2"><StatusBadge value={document.analysis_status} /></div>{document.analysis_error && <p className="text-xs text-red-600 mt-2 max-w-xl">{document.analysis_error}</p>}</div></div><div className="flex gap-1.5 items-start shrink-0 flex-wrap"><Button secondary disabled={previewBusy} onClick={() => void openPreview(document)}><Eye size={14} />View</Button><button className="cf-icon-button" aria-label={`Download ${document.title}`} onClick={() => void apiDownload(`/people/${personId}/documents/${document.id}/download`, document.original_filename).catch((error: unknown) => setPreviewError(error instanceof Error ? error.message : "Download failed."))}><Download size={15} /></button>{canWrite && <><Button secondary disabled={analysisMode !== null || uploadMutation.isPending || document.analysis_status === "processing"} onClick={() => analyze.mutate(document.id)}><Sparkles size={13} />{document.analysis_status === "not_analyzed" ? "Analyze" : "Analyze again"}</Button><button className="cf-icon-button" aria-label={`Delete ${document.title}`} disabled={remove.isPending || analysisMode !== null || document.analysis_status === "processing"} onClick={() => { if (window.confirm(`Delete ${document.title}? This removes the stored document.`)) remove.mutate(document.id); }}><Trash2 size={15} /></button></>}</div></div></article>)}</div> : <EmptyCapability icon={FileText} title={documentSearch ? "No matching documents" : "Start with a CV"} text={documentSearch ? "Try another filename." : "Upload supporting evidence. Analyze it to create reviewable profile suggestions."} />}{(analyze.error || batchError || previewError || remove.error) && <p role="alert" className="cf-alert cf-alert-error mt-5">{previewError ?? batchError ?? analyze.error?.message ?? remove.error?.message}</p>}</section>
    </>}
    {view === "review" && <section><div className="cf-panel-heading"><div><h2 className="text-lg font-semibold">AI review <span className="text-slate-400 font-normal ml-2">{pendingCount}</span></h2><p className="text-xs text-slate-500 mt-2">Review source evidence before accepting. AI confidence is not verification.</p></div>{canReview && pendingCount > 0 && <Button disabled={reviewBusy} onClick={() => { if (window.confirm(`Accept all ${pendingCount} pending suggestions, including those hidden by filters?`)) acceptAll.mutate(); }}><Check size={14} />{acceptAll.isPending ? "Accepting..." : "Accept all"}</Button>}</div><div className="cf-toolbar"><label className="cf-search"><Search size={15} /><input value={reviewSearch} onChange={(event) => { setReviewSearch(event.target.value); setReviewPage(1); }} aria-label="Search suggestions" placeholder="Search suggestions or source..." /></label><select className="cf-select" value={reviewFilter} aria-label="Filter suggestion category" onChange={(event) => { setReviewFilter(event.target.value); setReviewPage(1); }}><option value="">All categories</option>{["profile", "skill", "education", "certification", "employment", "project"].map((value) => <option value={value} key={value}>{value.charAt(0).toUpperCase() + value.slice(1)}</option>)}</select></div>{suggestions.isLoading ? <Skeleton rows={4} /> : suggestions.error ? <p className="cf-alert cf-alert-error">{suggestions.error.message}</p> : visibleSuggestions.length ? <><div className="space-y-3">{visibleSuggestions.map((suggestion) => <SuggestionCard key={suggestion.id} suggestion={suggestion} source={documentById.get(suggestion.source_document_id)} expanded={expanded === suggestion.id || editingId === suggestion.id} isEditing={editingId === suggestion.id} busy={reviewBusy} canReview={canReview} previewBusy={previewBusy} editPayload={editPayload} note={reviewNotes[suggestion.id] ?? suggestion.review_note ?? ""} onToggle={() => setExpanded((current) => current === suggestion.id ? null : suggestion.id)} onAccept={() => accept.mutate(suggestion)} onReject={() => reject.mutate(suggestion)} onEdit={() => startEditing(suggestion)} onSave={() => acceptEdited.mutate(suggestion)} onCancel={() => { setEditingId(null); setEditPayload({}); }} onChange={updateEditValue} onNote={(value) => setReviewNotes((current) => ({ ...current, [suggestion.id]: value }))} onPreview={(doc) => void openPreview(doc)} />)}</div><Pagination page={currentReviewPage} total={filteredSuggestions.length} pageSize={20} onChange={setReviewPage} /></> : <div className="cf-panel"><EmptyCapability icon={Check} title={pendingCount ? "No matching suggestions" : "Nothing waiting for review"} text={pendingCount ? "Change your search or category filter." : "Analyze evidence in the Documents tab to propose new profile information."} /></div>}{acceptAll.isPending && <p role="status" className="cf-alert mt-4">{batchProgress}</p>}{(accept.error || reject.error || acceptEdited.error || acceptAll.error || batchError || previewError) && <p role="alert" className="cf-alert cf-alert-error mt-4">{previewError ?? batchError ?? accept.error?.message ?? reject.error?.message ?? acceptEdited.error?.message ?? acceptAll.error?.message}</p>}</section>}
    {preview && <Modal title={preview.document.title} wide onClose={closePreview}><div className="flex items-center justify-between gap-3 mb-4"><p className="text-xs text-slate-400 truncate">{preview.document.original_filename}</p><Button secondary onClick={() => void apiDownload(`/people/${personId}/documents/${preview.document.id}/download`, preview.document.original_filename).catch((error: unknown) => setPreviewError(error instanceof Error ? error.message : "Download failed."))}><Download size={14} />Download</Button></div>{previewError && <p className="cf-alert cf-alert-error mb-4">{previewError}</p>}{preview.kind === "pdf" && preview.objectUrl && <iframe title={preview.document.title} src={preview.objectUrl} className="w-full h-[65vh] rounded-lg border border-slate-200" />}{preview.kind === "image" && preview.objectUrl && <img alt={preview.document.title} src={preview.objectUrl} className="max-h-[65vh] mx-auto object-contain" />}{preview.kind === "text" && <pre className="whitespace-pre-wrap break-words text-sm leading-7 font-sans text-slate-600 max-h-[65vh] overflow-auto">{preview.text}</pre>}</Modal>}
  </div>;
}
