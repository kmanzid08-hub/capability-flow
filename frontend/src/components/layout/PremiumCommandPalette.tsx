import { useEffect, useState } from "react";

export function PremiumCommandPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/20 p-10">
      <div className="mx-auto max-w-xl rounded-3xl bg-white p-6 shadow-xl">
        Search Capability Flow
      </div>
    </div>
  );
}
