import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, FileText, Link2, LoaderCircle, Paperclip, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Field, TextArea } from "../../components/ui";
import { api, apiUpload, LARGE_UPLOAD_TIMEOUT_MS, OPPORTUNITY_ANALYSIS_TIMEOUT_MS } from "../../lib/api";
import { qk } from "../../lib/queryKeys";
import { useWorkspace } from "../../lib/workspace";
import type { Opportunity, OpportunityAnalysis } from "../../types";
import type { OpportunityIntakeResponse } from "./shared";

export function IntakeForm({ compact = false, opportunityId, onComplete, onBusyChange }: {
  compact?: boolean; opportunityId?: string; onComplete?: (opportunity: Opportunity) => void; onBusyChange?: (busy: boolean) => void;
}) {
  const navigate = useNavigate(); const queryClient = useQueryClient(); const { canWrite } = useWorkspace();
  const [mode, setMode] = useState<"file" | "url" | "text">("file");
  const [title, setTitle] = useState(""); const [clientName, setClientName] = useState("");
  const [url, setUrl] = useState(""); const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null); const [autoAnalyze, setAutoAnalyze] = useState(true);
  const [phase, setPhase] = useState(""); const [percent, setPercent] = useState(0);
  const [savedId, setSavedId] = useState<string | null>(null);
  const saved = useRef<string | null>(null);
  const refresh = (id: string) => {
    void queryClient.invalidateQueries({ queryKey: qk("opportunities") });
    for (const key of ["opportunity", "opportunity-sources", "opportunity-analysis", "opportunity-roles", "opportunity-teams", "opportunity-gaps"]) void queryClient.invalidateQueries({ queryKey: qk(key, id) });
  };
  const mutation = useMutation({
    mutationFn: async () => {
      if (!canWrite) throw new Error("Write access is required.");
      let id = saved.current;
      if (!id) {
        if (mode === "file" && !file) throw new Error("Choose an opportunity document first.");
        if (file && mode === "file" && (file.size === 0 || file.size > 250 * 1024 * 1024)) throw new Error("Select a non-empty file no larger than 250 MB.");
        if (mode === "url" && !/^https?:\/\//i.test(url.trim())) throw new Error("Enter a complete http:// or https:// URL.");
        if (mode === "text" && text.trim().length < 20) throw new Error("Paste at least 20 characters of source text.");
        setPhase(mode === "file" ? "Uploading your source" : "Saving your source"); setPercent(0);
        if (opportunityId) {
          if (mode === "file") { const form = new FormData(); form.append("file", file!); await apiUpload(`/opportunities/${opportunityId}/sources/file`, form, setPercent); }
          else await api(`/opportunities/${opportunityId}/sources/${mode}`, { method: "POST", body: JSON.stringify(mode === "url" ? { url: url.trim() } : { text: text.trim() }), timeoutMs: LARGE_UPLOAD_TIMEOUT_MS });
          id = opportunityId;
        } else {
          let intake: OpportunityIntakeResponse;
          if (mode === "file") { const form = new FormData(); form.append("file", file!); if (title.trim()) form.append("title", title.trim()); if (clientName.trim()) form.append("client_name", clientName.trim()); intake = await apiUpload<OpportunityIntakeResponse>("/opportunities/intake/file", form, setPercent); }
          else intake = await api<OpportunityIntakeResponse>(`/opportunities/intake/${mode}`, { method: "POST", body: JSON.stringify({ ...(mode === "url" ? { url: url.trim() } : { text: text.trim() }), title: title.trim() || null, client_name: clientName.trim() || null }), timeoutMs: LARGE_UPLOAD_TIMEOUT_MS });
          id = intake.opportunity.id;
        }
        saved.current = id; setSavedId(id); refresh(id);
      }
      if (autoAnalyze) {
        setPhase("Analyzing requirements and matching your team");
        await api<OpportunityAnalysis>(`/opportunities/${id}/analyze`, { method: "POST", timeoutMs: OPPORTUNITY_ANALYSIS_TIMEOUT_MS });
      }
      return api<Opportunity>(`/opportunities/${id}`);
    }, onSuccess: (opportunity) => { refresh(opportunity.id); onComplete?.(opportunity); if (!opportunityId) navigate(`/opportunities/${opportunity.id}`); }, onError: () => { if (saved.current) refresh(saved.current); }
  });
  useEffect(() => { onBusyChange?.(mutation.isPending); return () => onBusyChange?.(false); }, [mutation.isPending, onBusyChange]);
  const eligible = savedId || (mode === "file" ? file && file.size > 0 : mode === "url" ? url.trim() : text.trim().length >= 20);
  return <section className={compact ? "" : "cf-panel"}><h2 className="text-base font-semibold">{opportunityId ? "Add a source" : "Start with the source"}</h2><p className="mt-2 text-xs text-slate-500 leading-6">Upload the brief, paste its text, or use a public link. Original requirements remain available for review.</p>
    <fieldset disabled={mutation.isPending || Boolean(savedId)} className="min-w-0 mt-5"><div className="cf-view-toggle mb-5">{([["file", "Upload file", Paperclip], ["url", "Website URL", Link2], ["text", "Paste text", FileText]] as const).map(([value, label, Icon]) => <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)} className="inline-flex items-center gap-2 text-xs !py-2 !px-3"><Icon size={13} />{label}</button>)}</div>
      {mode === "file" && <div className="cf-upload-zone"><label className="cf-field"><span>Tender, TOR, or client brief</span><input type="file" accept=".pdf,.docx,.xlsx,.xlsm,.pptx,.txt,.csv,.rtf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="block w-full text-xs text-slate-500 mt-3 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-slate-700" /></label><p className="text-[11px] text-slate-400 mt-3">PDF, Word, spreadsheets, slides, or text. Up to 250 MB.</p>{file && <p className="text-xs mt-3">{file.name} <span className="text-slate-400">/ {(file.size / (1024 * 1024)).toFixed(1)} MB</span></p>}</div>}
      {mode === "url" && <Field label="Public source URL" type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.org/tenders/..." />}
      {mode === "text" && <TextArea label="Client requirement or brief" rows={8} value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the complete requirement, TOR, or RFP text." />}
      {!opportunityId && <details className="mt-5"><summary className="cursor-pointer text-xs text-slate-500">Title and client <span className="text-slate-400">(optional)</span></summary><div className="grid sm:grid-cols-2 gap-4 mt-4"><Field label="Opportunity title" placeholder="Detect from the source" value={title} onChange={(e) => setTitle(e.target.value)} /><Field label="Client" placeholder="Detect from the source" value={clientName} onChange={(e) => setClientName(e.target.value)} /></div></details>}</fieldset>
    <label className="flex gap-2.5 items-center text-xs text-slate-500 mt-5"><input type="checkbox" disabled={mutation.isPending} checked={autoAnalyze} onChange={(e) => setAutoAnalyze(e.target.checked)} />Analyze after saving</label>
    {mutation.isPending && <div className="cf-alert mt-5" role="status"><div className="flex items-center gap-2"><LoaderCircle size={14} className="animate-spin" /><span>{phase}</span></div>{mode === "file" && !savedId && <><progress value={percent} max={100} aria-label="Source upload progress" className="w-full h-1 mt-3 accent-slate-700" /><p className="text-xs text-slate-400 mt-2">{percent < 100 ? `${percent}% transmitted` : "File transmitted. The server is saving and reading the source."}</p></>}<p className="text-xs text-slate-400 mt-2">Large files and provider fallbacks can take several minutes.</p></div>}
    {mutation.error && <div role="alert" className="cf-alert cf-alert-error mt-5">{mutation.error.message}{savedId && <p className="mt-2">Your source was saved. Retrying will not upload it again. <Link className="underline" to={`/opportunities/${savedId}`}>Open the opportunity</Link></p>}</div>}
    <div className="mt-6 flex items-center justify-between gap-3"><Button disabled={!eligible || mutation.isPending || !canWrite} onClick={() => mutation.mutate()}>{autoAnalyze ? <Sparkles size={14} /> : <ArrowRight size={14} />}{mutation.isPending ? "Working..." : savedId ? "Retry analysis" : autoAnalyze ? "Save & analyze" : "Save source"}</Button>{savedId && mutation.isPending && <Link className="cf-link" to={`/opportunities/${savedId}`}>Open workspace<ArrowRight size={13} /></Link>}</div>
  </section>;
}
