export function Toast({ message }: { message: string }) {
  return (
    <div className="fixed bottom-6 right-6 rounded-2xl border bg-white px-5 py-4 shadow-lg">
      {message}
    </div>
  );
}
