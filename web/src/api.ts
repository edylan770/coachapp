import type { TokenPair } from "./types";

const TOKEN_KEY = "traineros.tokens";

interface StoredTokens {
  access_token: string;
  refresh_token: string;
}

let tokens: StoredTokens | null = (() => {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as StoredTokens) : null;
  } catch {
    return null;
  }
})();

export function hasTokens(): boolean {
  return tokens !== null;
}

export function setTokens(pair: TokenPair): void {
  tokens = { access_token: pair.access_token, refresh_token: pair.refresh_token };
  localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

export function clearTokens(): void {
  tokens = null;
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

// Single-flight refresh so parallel 401s don't burn the rotating token.
let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  refreshing ??= (async () => {
    if (!tokens) return false;
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      });
      if (!res.ok) {
        clearTokens();
        return false;
      }
      setTokens((await res.json()) as TokenPair);
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => (refreshing = null), 0);
    }
  })();
  return refreshing;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const doFetch = () =>
    fetch(`/api${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(auth && tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });

  let res = await doFetch();
  if (res.status === 401 && auth && tokens && (await tryRefresh())) {
    res = await doFetch();
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) {
        detail = data.detail[0].msg as string;
      }
    } catch {
      // keep default detail
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}
