import {
  Radar
} from "lucide-react";


export function ScoreRing({
  score,
  label,
}: {
  score: number | null | undefined;
  label: string;
}) {
  const hasScore = score != null;
  const normalized = hasScore
    ? Math.max(0, Math.min(100, score))
    : 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-xs font-medium tracking-wide text-slate-400">
        {label}
      </p>

      <div className="mt-4 flex items-end gap-2">
        <strong className="font-serif text-4xl text-evergreen">
          {hasScore ? Math.round(normalized) : "—"}
        </strong>
        <span className="pb-1 text-sm text-slate-400">
          / 100
        </span>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-evergreen transition-all"
          style={{
            width: `${normalized}%`,
          }}
        />
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
      <Radar
        size={34}
        className="mx-auto text-slate-300"
      />
      <h3 className="mt-4 font-serif text-2xl">
        {title}
      </h3>
      <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
        {text}
      </p>
    </div>
  );
}
