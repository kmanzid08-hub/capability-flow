import { BarChart3, Building2, LogOut, Menu, Users, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { session } from "../lib/session";

const links = [{ to: "/", label: "Overview", icon: BarChart3 }, { to: "/people", label: "People", icon: Users }, { to: "/organization", label: "Organization", icon: Building2 }];
export function AppLayout() {
  const [open, setOpen] = useState(false); const navigate = useNavigate();
  const logout = () => { session.clear(); navigate("/login"); };
  return <div className="min-h-screen bg-[#f7f8f5] text-ink">
    <button className="fixed left-4 top-4 z-50 rounded-xl bg-evergreen p-2 text-white lg:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu">{open ? <X /> : <Menu />}</button>
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-ink px-5 py-7 text-white transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="mb-10 flex items-center gap-3 px-2"><div className="grid h-10 w-10 place-items-center rounded-xl bg-coral font-serif text-xl">C</div><div><p className="font-serif text-xl">Capability Flow</p><p className="text-xs text-white/50">Organizational readiness</p></div></div>
      <nav className="space-y-2">{links.map(({to,label,icon:Icon}) => <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)} className={({isActive}) => `flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${isActive ? "bg-white/12 text-white" : "text-white/60 hover:bg-white/5 hover:text-white"}`}><Icon size={18}/>{label}</NavLink>)}</nav>
      <div className="mt-auto border-t border-white/10 pt-5"><button onClick={logout} className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm text-white/60 hover:bg-white/5 hover:text-white"><LogOut size={18}/>Sign out</button></div>
    </aside>
    <main className="min-h-screen lg:ml-72"><Outlet /></main>
  </div>;
}

