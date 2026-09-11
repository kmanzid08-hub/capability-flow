export function Skeleton({ rows = 5, title = "Loading" }: { rows?: number; title?: string; }) {
  return <div role="status" aria-label={title} className="cf-skeleton-list"><span className="sr-only">{title}</span>
    {Array.from({ length: rows }, (_, i) => <div className="cf-skeleton-row" key={i} aria-hidden="true"><div className="cf-skeleton cf-skeleton-avatar" /><div className="flex-1 space-y-3"><div className="cf-skeleton h-3 w-2/5" /><div className="cf-skeleton h-2.5 w-3/5" /></div></div>)}
  </div>;
}
export function PageSkeleton() {
  return <div className="cf-page" role="status" aria-label="Loading workspace"><div className="cf-skeleton h-8 w-48 mb-8" /><Skeleton rows={5} /></div>;
}
