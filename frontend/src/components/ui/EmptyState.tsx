import { Layers2 } from "lucide-react";
import type { ReactNode } from "react";
export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode; }) {
  return <div className="cf-empty"><div className="cf-empty-icon"><Layers2 size={22} /></div><h3>{title}</h3><p>{description}</p>{action && <div className="mt-5">{action}</div>}</div>;
}
