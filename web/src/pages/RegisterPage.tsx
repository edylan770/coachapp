import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, errorMessage, setTokens } from "../api";
import type { TokenPair, User } from "../types";

export function RegisterPage() {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api<User>("/auth/register", {
        method: "POST",
        body: { email, password, display_name: displayName || null },
        auth: false,
      });
      const pair = await api<TokenPair>("/auth/login", {
        method: "POST",
        body: { email, password },
        auth: false,
      });
      setTokens(pair);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold">Create your trainer account</h1>
        <p className="text-sm text-slate-400">
          Clients don't sign up here — you'll invite them once you're in.
        </p>
        <div>
          <label className="label" htmlFor="displayName">
            Display name
          </label>
          <input
            id="displayName"
            className="input w-full"
            placeholder="Coach Sam"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            className="input w-full"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="password">
            Password (min 8 characters)
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            className="input w-full"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button type="submit" className="btn w-full" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
        <p className="text-sm text-slate-400">
          Already registered?{" "}
          <Link className="text-emerald-400 hover:underline" to="/login">
            Sign in
          </Link>
        </p>
      </form>
    </main>
  );
}
