export function CapabilityScore({ score }: { score: number }) {
  return (
    <div className="rounded-3xl border bg-white p-6">
      <div className="text-sm text-slate-500">Capability strength</div>
      <div className="text-4xl font-semibold">{score}%</div>
    </div>
  );
}
