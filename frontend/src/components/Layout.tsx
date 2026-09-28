import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  LogOut,
  Package,
  Boxes,
  Receipt,
  Store,
  Undo2,
} from "lucide-react";
import { useAuth } from "../context/auth";
import { titleCase } from "../lib/format";
import { cn } from "./ui";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/pos", label: "POS / Checkout", icon: Store, end: false },
  { to: "/products", label: "Products", icon: Package, end: false },
  { to: "/inventory", label: "Inventory", icon: Boxes, end: false },
  { to: "/transactions", label: "Transactions", icon: Receipt, end: false },
  { to: "/refunds", label: "Refunds", icon: Undo2, end: false },
];

export function Protected(): React.JSX.Element {
  const { user, checking } = useAuth();
  if (checking) return <div className="grid min-h-screen place-items-center text-sm text-neutral-400">Checking session…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen bg-neutral-50">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-neutral-200 bg-white md:flex">
        <div className="flex items-center gap-2 border-b border-neutral-200 px-5 py-4">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-neutral-900 text-sm font-bold text-white">P</span>
          <div>
            <div className="text-sm font-semibold leading-none text-neutral-900">PITSTOP POS</div>
            <div className="mt-0.5 text-xs text-neutral-400">v1.0.0</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-neutral-900 text-white" : "text-neutral-600 hover:bg-neutral-100",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-neutral-200 p-3">
          <div className="mb-2 px-3 text-xs text-neutral-400">
            {user?.full_name || user?.username}
            <span className="ml-2 rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-500">
              {user ? titleCase(user.role) : ""}
            </span>
          </div>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-neutral-600 hover:bg-red-50 hover:text-red-600"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-3 md:hidden">
          <span className="font-semibold text-neutral-900">PITSTOP POS</span>
          <button onClick={() => navigate("/")} className="text-sm text-neutral-500">
            Menu
          </button>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}