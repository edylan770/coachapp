import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, errorMessage } from "../api";
import type { Client, ClientStatus, ClientWithInvite } from "../types";

const statusStyles: Record<ClientStatus, string> = {
  invited: "bg-amber-950 text-amber-400 border-amber-900",
  active: "bg-emerald-950 text-emerald-400 border-emerald-900",
  paused: "bg-slate-800 text-slate-400 border-slate-700",
};

function InviteTokenBox({ invite }: { invite: ClientWithInvite }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="card border-emerald-900 bg-emerald-950/30">
      <p className="text-sm text-slate-300">
        Invite for <strong>{invite.full_name}</strong> — share this token with them now;
        it won't be shown again. They redeem it in the client app (or via
        <code className="mx-1 rounded bg-slate-800 px-1">POST /auth/accept-invite</code>
        until the app ships).
      </p>
      <div className="mt-2 flex items-center gap-2">
        <code className="flex-1 overflow-x-auto rounded bg-slate-900 px-2 py-1.5 text-xs text-emerald-300">
          {invite.invite_token}
        </code>
        <button
          type="button"
          className="btn-ghost shrink-0"
          onClick={() => {
            void navigator.clipboard.writeText(invite.invite_token);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
    </div>
  );
}

export function ClientsPage() {
  const queryClient = useQueryClient();
  const clients = useQuery({ queryKey: ["clients"], queryFn: () => api<Client[]>("/clients") });

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [lastInvite, setLastInvite] = useState<ClientWithInvite | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["clients"] });

  const invite = useMutation({
    mutationFn: () =>
      api<ClientWithInvite>("/clients", {
        method: "POST",
        body: { email, full_name: fullName },
      }),
    onSuccess: (data) => {
      setLastInvite(data);
      setFullName("");
      setEmail("");
      setError(null);
      void refresh();
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const reinvite = useMutation({
    mutationFn: (clientId: string) =>
      api<ClientWithInvite>(`/clients/${clientId}/reinvite`, { method: "POST" }),
    onSuccess: (data) => {
      setLastInvite(data);
      setError(null);
      void refresh();
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const setStatus = useMutation({
    mutationFn: ({ clientId, status }: { clientId: string; status: "active" | "paused" }) =>
      api<Client>(`/clients/${clientId}`, { method: "PATCH", body: { status } }),
    onSuccess: () => void refresh(),
    onError: (err) => setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (clientId: string) => api<void>(`/clients/${clientId}`, { method: "DELETE" }),
    onSuccess: () => void refresh(),
    onError: (err) => setError(errorMessage(err)),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Clients</h1>
      </div>

      <form
        className="card flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          invite.mutate();
        }}
      >
        <div>
          <label className="label" htmlFor="inviteName">
            Full name
          </label>
          <input
            id="inviteName"
            required
            className="input"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </div>
        <div className="grow">
          <label className="label" htmlFor="inviteEmail">
            Email
          </label>
          <input
            id="inviteEmail"
            type="email"
            required
            className="input w-full"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <button type="submit" className="btn" disabled={invite.isPending}>
          Invite client
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {lastInvite && <InviteTokenBox invite={lastInvite} />}

      <div className="card overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {clients.data?.map((c) => (
              <tr key={c.id} className="border-b border-slate-800/60 last:border-0">
                <td className="px-4 py-3 font-medium">{c.full_name}</td>
                <td className="px-4 py-3 text-slate-400">{c.email}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs ${statusStyles[c.status]}`}
                  >
                    {c.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    {c.status === "invited" && (
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => reinvite.mutate(c.id)}
                      >
                        New invite token
                      </button>
                    )}
                    {c.status === "active" && (
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => setStatus.mutate({ clientId: c.id, status: "paused" })}
                      >
                        Pause
                      </button>
                    )}
                    {c.status === "paused" && (
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => setStatus.mutate({ clientId: c.id, status: "active" })}
                      >
                        Reactivate
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => {
                        if (window.confirm(`Remove ${c.full_name}? This deletes their account.`)) {
                          remove.mutate(c.id);
                        }
                      }}
                    >
                      Remove
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {clients.data?.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                  No clients yet — invite your first one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
