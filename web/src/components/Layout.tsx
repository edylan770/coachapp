import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { api, clearTokens } from "../api";
import type { Trainer } from "../types";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${
    isActive ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"
  }`;

export function Layout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const me = useQuery({
    queryKey: ["trainers", "me"],
    queryFn: () => api<Trainer>("/trainers/me"),
  });

  const logout = () => {
    clearTokens();
    queryClient.clear();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
          <span className="text-lg font-semibold tracking-tight text-emerald-400">
            TrainerOS
          </span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={navClass}>
              Programs
            </NavLink>
            <NavLink to="/clients" className={navClass}>
              Clients
            </NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-400">
            {me.data && <span>{me.data.display_name}</span>}
            <button type="button" className="btn-ghost" onClick={logout}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
