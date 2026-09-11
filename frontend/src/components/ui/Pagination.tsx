import { ChevronLeft, ChevronRight } from "lucide-react";
export function Pagination({ page, total, pageSize, onChange, onSizeChange }: {
  page: number; total: number; pageSize: number; onChange: (page: number) => void; onSizeChange?: (size: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.max(1, Math.min(Math.floor(page) || 1, pages));
  return <nav className="cf-pagination" aria-label="Pagination"><p>{total ? (safePage - 1) * pageSize + 1 : 0} - {Math.min(safePage * pageSize, total)} of {total}</p>
    <div className="flex items-center gap-3">
      {onSizeChange && <select className="cf-select" aria-label="Rows per page" value={pageSize} onChange={(e) => onSizeChange(Number(e.target.value))}><option value={25}>25 per page</option><option value={50}>50 per page</option></select>}
      <span className="text-xs text-slate-500">Page {safePage} of {pages}</span>
      <button className="cf-icon-button" aria-label="Previous page" disabled={safePage <= 1} onClick={() => onChange(safePage - 1)}><ChevronLeft size={17} /></button>
      <button className="cf-icon-button" aria-label="Next page" disabled={safePage >= pages} onClick={() => onChange(safePage + 1)}><ChevronRight size={17} /></button>
    </div></nav>;
}
