import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";

/** Native dialog supplies modal semantics, Escape handling and focus containment. */
export function Modal({ title, children, onClose, busy = false, wide = false }: {
  title: string; children: ReactNode; onClose: () => void; busy?: boolean; wide?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const el = dialog.current;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    el?.showModal();
    document.body.style.overflow = "hidden";
    return () => { el?.close(); document.body.style.overflow = overflow; previous?.focus(); };
  }, []);
  return <dialog ref={dialog} className={`cf-modal ${wide ? "cf-modal-wide" : ""}`} aria-labelledby={titleId}
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget && !busy) { const r = event.currentTarget.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) onClose(); } }}>
    <header className="cf-modal-header"><h2 id={titleId}>{title}</h2><button type="button" className="cf-icon-button" aria-label="Close dialog" disabled={busy} onClick={onClose}><X size={18} /></button></header>
    <div className="cf-modal-body">{children}</div>
  </dialog>;
}
