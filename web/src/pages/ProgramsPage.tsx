import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, errorMessage } from "../api";
import type { Client, Program, ProgramDetail } from "../types";

export function ProgramsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const programs = useQuery({
    queryKey: ["programs"],
    queryFn: () => api<Program[]>("/programs"),
  });
  const clients = useQuery({ queryKey: ["clients"], queryFn: () => api<Client[]>("/clients") });

  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["programs"] });

  const create = useMutation({
    mutationFn: () => api<ProgramDetail>("/programs", { method: "POST", body: { name } }),
    onSuccess: (program) => navigate(`/programs/${program.id}`),
    onError: (err) => setError(errorMessage(err)),
  });

  const assign = useMutation({
    mutationFn: ({ programId, clientId }: { programId: string; clientId: string | null }) =>
      api<Program>(`/programs/${programId}`, { method: "PATCH", body: { client_id: clientId } }),
    onSuccess: () => void refresh(),
    onError: (err) => setError(errorMessage(err)),
  });

  const duplicate = useMutation({
    mutationFn: ({ programId, asTemplate }: { programId: string; asTemplate: boolean }) =>
      api<ProgramDetail>(`/programs/${programId}/duplicate`, {
        method: "POST",
        body: { as_template: asTemplate },
      }),
    onSuccess: () => void refresh(),
    onError: (err) => setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (programId: string) => api<void>(`/programs/${programId}`, { method: "DELETE" }),
    onSuccess: () => void refresh(),
    onError: (err) => setError(errorMessage(err)),
  });

  const clientName = (clientId: string | null) =>
    clients.data?.find((c) => c.id === clientId)?.full_name ?? null;

  const renderRow = (program: Program) => (
    <tr key={program.id} className="border-b border-slate-800/60 last:border-0">
      <td className="px-4 py-3">
        <Link
          to={`/programs/${program.id}`}
          className="font-medium text-emerald-400 hover:underline"
        >
          {program.name}
        </Link>
        <span className="ml-2 text-xs text-slate-500">v{program.version}</span>
      </td>
      <td className="px-4 py-3">
        {program.is_template ? (
          <span className="text-slate-500">—</span>
        ) : (
          <select
            className="select"
            value={program.client_id ?? ""}
            onChange={(e) =>
              assign.mutate({ programId: program.id, clientId: e.target.value || null })
            }
          >
            <option value="">Unassigned</option>
            {clients.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </select>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => duplicate.mutate({ programId: program.id, asTemplate: false })}
          >
            Duplicate
          </button>
          {!program.is_template && (
            <button
              type="button"
              className="btn-ghost"
              onClick={() => duplicate.mutate({ programId: program.id, asTemplate: true })}
            >
              Save as template
            </button>
          )}
          <button
            type="button"
            className="btn-danger"
            onClick={() => {
              if (window.confirm(`Delete "${program.name}"?`)) remove.mutate(program.id);
            }}
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  );

  const regular = programs.data?.filter((p) => !p.is_template) ?? [];
  const templates = programs.data?.filter((p) => p.is_template) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Programs</h1>
      </div>

      <form
        className="card flex items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <div className="grow">
          <label className="label" htmlFor="programName">
            New program name
          </label>
          <input
            id="programName"
            required
            className="input w-full"
            placeholder="e.g. Hypertrophy Base — 8 weeks"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <button type="submit" className="btn" disabled={create.isPending}>
          Create &amp; open builder
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <section className="space-y-2">
        <h2 className="text-sm font-medium uppercase tracking-wide text-slate-400">Programs</h2>
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Assigned to</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {regular.map(renderRow)}
              {regular.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-slate-500">
                    No programs yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {assign.isPending && <p className="text-xs text-slate-500">Updating assignment…</p>}
        {regular.some((p) => p.client_id) && (
          <p className="text-xs text-slate-500">
            Assigned: {regular
              .filter((p) => p.client_id)
              .map((p) => `${p.name} → ${clientName(p.client_id) ?? "?"}`)
              .join(", ")}
          </p>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium uppercase tracking-wide text-slate-400">Templates</h2>
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <tbody>
              {templates.map(renderRow)}
              {templates.length === 0 && (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500">
                    No templates — use "Save as template" on a program.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
