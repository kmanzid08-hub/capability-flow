export function CapabilityScore({ score }: { score: number }) {
  return (
    <section className="cf-panel">
      <p className="text-xs text-slate-400">Capability readiness</p>
      <p className="mt-2 text-4xl font-semibold">{score}%</p>
      <div className="mt-4 h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-black" style={{ width: `${score}%` }} />
      </div>
    </section>
  );
}
