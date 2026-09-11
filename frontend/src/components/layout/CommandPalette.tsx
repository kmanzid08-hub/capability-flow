import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BriefcaseBusiness, GitBranch, LayoutDashboard, Plus, Search, Settings2, Users } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { directoryOptions } from "../../lib/people";
import { qk } from "../../lib/queryKeys";
import { useWorkspace } from "../../lib/workspace";
import type { Opportunity } from "../../types";
import { Modal } from "../ui/Modal";

type Item = { id: string; label: string; detail: string; to: string; icon: typeof Search; };
export function CommandPalette({ onClose }: { onClose: () => void; }) {
  const navigate = useNavigate();
  const { canWrite } = useWorkspace();
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const people = useQuery({ ...directoryOptions(), enabled: search.trim().length >= 2 });
  const opportunities = useQuery({ queryKey: qk("opportunities"), queryFn: ({ signal }) => api<Opportunity[]>("/opportunities", { signal }), enabled: search.trim().length >= 2 });
  useEffect(() => { input.current?.focus(); }, []);
  const items = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    const nav: Item[] = [
      { id: "overview", label: "Overview", detail: "Go to", to: "/", icon: LayoutDashboard },
      { id: "people", label: "People", detail: "Go to", to: "/people", icon: Users },
      { id: "opportunities", label: "Opportunities", detail: "Go to", to: "/opportunities", icon: BriefcaseBusiness },
      { id: "pipeline", label: "Pipeline", detail: "Go to", to: "/pipeline", icon: GitBranch },
      { id: "settings", label: "Workspace settings", detail: "Go to", to: "/organization", icon: Settings2 },
      ...(canWrite ? [{ id: "create-person", label: "Add person", detail: "Create", to: "/people/new", icon: Plus }, { id: "create-opportunity", label: "New opportunity", detail: "Create", to: "/opportunities?new=1", icon: Plus }] : []),
    ];
    return [
      ...nav.filter((item) => item.label.toLocaleLowerCase().includes(term)),
      ...(term.length >= 2 ? (people.data ?? []).filter((p) => `${p.display_name} ${p.professional_title ?? ""}`.toLocaleLowerCase().includes(term)).slice(0, 7).map((p) => ({ id: p.id, label: p.display_name, detail: "Person", to: `/people/${p.id}`, icon: Users })) : []),
      ...(term.length >= 2 ? (opportunities.data ?? []).filter((o) => `${o.title} ${o.client_name ?? ""}`.toLocaleLowerCase().includes(term)).slice(0, 5).map((o) => ({ id: o.id, label: o.title, detail: "Opportunity", to: `/opportunities/${o.id}`, icon: BriefcaseBusiness })) : []),
    ];
  }, [search, people.data, opportunities.data, canWrite]);
  const selected = Math.min(active, Math.max(items.length - 1, 0));
  const go = (item: Item) => { onClose(); navigate(item.to); };
  return <Modal title="Find anything" onClose={onClose}>
    <div className="cf-command-input"><Search size={19} /><input ref={input} value={search} placeholder="People, opportunities, or a command..." aria-label="Search workspace" role="combobox" aria-expanded="true" aria-controls="cf-command-results" aria-activedescendant={items[selected] ? `command-${items[selected].id}` : undefined}
      onChange={(event) => { setSearch(event.target.value); setActive(0); }}
      onKeyDown={(event) => { if (event.key === "ArrowDown") { event.preventDefault(); setActive((v) => Math.min(v + 1, items.length - 1)); } if (event.key === "ArrowUp") { event.preventDefault(); setActive((v) => Math.max(v - 1, 0)); } if (event.key === "Enter" && items[selected]) { event.preventDefault(); go(items[selected]); } }} /></div>
    <ul className="cf-command-list" id="cf-command-results" role="listbox" aria-label="Search results">{items.map((item, index) => <li key={item.id} role="none"><button id={`command-${item.id}`} role="option" aria-selected={selected === index} className="cf-command-item" onMouseEnter={() => setActive(index)} onClick={() => go(item)}><span className="flex min-w-0 items-center gap-3"><item.icon size={16} className="text-slate-400 shrink-0" /><span className="truncate text-sm">{item.label}</span></span><span className="flex shrink-0 items-center gap-3 text-xs text-slate-400">{item.detail}<ArrowUpRight size={13} /></span></button></li>)}</ul>
    {!items.length && <p className="py-8 text-center text-sm text-slate-400">{people.isFetching || opportunities.isFetching ? "Searching your workspace..." : "No results found."}</p>}
    {(people.error || opportunities.error) && <p className="cf-alert cf-alert-error">Some search results could not load. Navigation commands remain available.</p>}
    <p className="border-t border-slate-100 pt-3 text-[11px] text-slate-400">Use arrow keys to navigate, Enter to open, and Escape to close.</p>
  </Modal>;
}
