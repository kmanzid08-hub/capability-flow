import type { ElementType } from "react";
export function EmptyCapability({ icon: Icon, title, text }: { icon: ElementType; title: string; text: string; }) {
  return <div className="cf-empty"><div className="cf-empty-icon"><Icon size={22} /></div><h3>{title}</h3><p>{text}</p></div>;
}
