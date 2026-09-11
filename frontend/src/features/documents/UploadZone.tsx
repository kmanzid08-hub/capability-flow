import { Upload } from "lucide-react";
import { useRef, useState } from "react";
const accepted = ".pdf,.doc,.docx,.xls,.xlsx,.xlsm,.csv,.tsv,.ppt,.pptx,.jpg,.jpeg,.png,.webp,.gif,.txt,.text,.md,.markdown,.rtf,.json,.jsonl,.xml,.html,.htm,.yaml,.yml,.odt,.ods,.odp";
export function UploadZone({ onFiles, disabled }: { onFiles: (files: File[]) => void; disabled: boolean; }) {
  const [dragging, setDragging] = useState(false); const input = useRef<HTMLInputElement>(null);
  return <div className="cf-upload-zone text-center" data-dragging={dragging} onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); if (!disabled) onFiles([...event.dataTransfer.files]); }}>
    <Upload size={21} className="text-slate-400 mx-auto mb-3" /><p className="text-sm text-slate-600">Drop documents here, or <button type="button" disabled={disabled} onClick={() => input.current?.click()} className="font-semibold text-ink underline underline-offset-4">choose files</button></p><p className="text-[11px] text-slate-400 mt-2">PDF, Word, spreadsheets, images and text</p><input ref={input} type="file" multiple accept={accepted} disabled={disabled} className="sr-only" aria-label="Select evidence documents" onChange={(event) => { onFiles(Array.from(event.target.files ?? [])); event.currentTarget.value = ""; }} />
  </div>;
}
