import { useQuery } from "@tanstack/react-query";

interface HealthResponse {
  status: string;
  database: string;
}

async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`API unhealthy (${res.status})`);
  return res.json();
}

export default function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth, retry: 1 });

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <div className="max-w-md space-y-3 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">TrainerOS</h1>
        <p className="text-slate-400">Trainer dashboard — Phase 0 scaffold</p>
        <p className="text-sm">
          API status:{" "}
          {health.isPending ? (
            <span className="text-slate-400">checking…</span>
          ) : health.isSuccess ? (
            <span className="text-emerald-400">{health.data.status}</span>
          ) : (
            <span className="text-red-400">unreachable</span>
          )}
        </p>
      </div>
    </main>
  );
}
