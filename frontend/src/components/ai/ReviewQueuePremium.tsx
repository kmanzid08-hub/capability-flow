export function ReviewQueuePremium({ suggestions }: { suggestions: any[] }) {
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">AI Review</h2>
      {suggestions.map((item) => (
        <div key={item.id} className="rounded-3xl border bg-white p-6">
          <div className="font-semibold">{item.title}</div>
          <div className="mt-2 text-sm text-slate-500">Evidence-backed suggestion</div>
        </div>
      ))}
    </section>
  );
}
