import {
  Building2,
  Gauge,
  GitBranch,
  LogOut,
  Radar,
  Users,
} from "lucide-react";
import {
  NavLink,
  Outlet,
  useNavigate,
} from "react-router-dom";

const navItems = [
  {
    to: "/",
    label: "Dashboard",
    icon: Gauge,
    end: true,
  },
  {
    to: "/opportunities",
    label: "Opportunities",
    icon: Radar,
    end: false,
  },
  {
    to: "/pipeline",
    label: "Pipeline",
    icon: GitBranch,
    end: false,
  },
  {
    to: "/people",
    label: "People",
    icon: Users,
    end: false,
  },
  {
    to: "/organization",
    label: "Organization",
    icon: Building2,
    end: false,
  },
];

export function AppLayout() {
  const navigate = useNavigate();

  const logout = () => {
    localStorage.clear();
    navigate("/login", {
      replace: true,
    });
  };

  return (
    <div className="min-h-screen bg-[#f8f7f2] text-ink lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="border-b border-white/10 bg-ink text-white lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between px-6 py-5 lg:block lg:px-7 lg:py-8">
          <NavLink
            to="/"
            className="flex items-center gap-3"
          >
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-coral font-serif text-lg">
              C
            </span>

            <span>
              <span className="block font-serif text-lg">
                Capability Flow
              </span>
              <span className="block text-[11px] uppercase tracking-[.18em] text-white/35">
                Capability intelligence
              </span>
            </span>
          </NavLink>

          <button
            type="button"
            onClick={logout}
            className="rounded-lg p-2 text-white/50 hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Sign out"
          >
            <LogOut size={18} />
          </button>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-4 pb-4 lg:block lg:space-y-1 lg:px-4">
          {navItems.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    "flex shrink-0 items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition",
                    isActive
                      ? "bg-white text-ink"
                      : "text-white/55 hover:bg-white/10 hover:text-white",
                  ].join(" ")
                }
              >
                <Icon size={18} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 hidden p-4 lg:block">
          <button
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-white/45 hover:bg-white/10 hover:text-white"
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0">
        <Outlet />
      </main>
    </div>
  );
}