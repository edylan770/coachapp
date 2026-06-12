import Constants from "expo-constants";
import * as SecureStore from "expo-secure-store";

import type { TokenPair } from "./types";

export const API_URL: string =
  (Constants.expoConfig?.extra as { apiUrl?: string } | undefined)?.apiUrl ??
  "http://localhost:8000";

const ACCESS_KEY = "traineros.access";
const REFRESH_KEY = "traineros.refresh";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let initialized = false;

const authListeners = new Set<() => void>();

export function onAuthChange(listener: () => void): () => void {
  authListeners.add(listener);
  return () => authListeners.delete(listener);
}

function emitAuthChange(): void {
  for (const listener of authListeners) listener();
}

export async function initAuth(): Promise<void> {
  if (initialized) return;
  accessToken = await SecureStore.getItemAsync(ACCESS_KEY);
  refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
  initialized = true;
}

export function isAuthed(): boolean {
  return refreshToken !== null;
}

async function storeTokens(pair: TokenPair): Promise<void> {
  accessToken = pair.access_token;
  refreshToken = pair.refresh_token;
  await SecureStore.setItemAsync(ACCESS_KEY, pair.access_token);
  await SecureStore.setItemAsync(REFRESH_KEY, pair.refresh_token);
  emitAuthChange();
}

export async function clearAuth(): Promise<void> {
  accessToken = null;
  refreshToken = null;
  await SecureStore.deleteItemAsync(ACCESS_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
  emitAuthChange();
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
    if (!refreshToken) return false;
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        if (res.status === 401) await clearAuth();
        return false;
      }
      await storeTokens((await res.json()) as TokenPair);
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => {
        refreshing = null;
      }, 0);
    }
  })();
  return refreshing;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  auth?: boolean;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, auth = true } = options;

  const doFetch = () =>
    fetch(`${API_URL}${path}`, {
      method,
      headers: {
        // Let fetch set the multipart boundary itself when sending FormData.
        ...(formData ? {} : { "Content-Type": "application/json" }),
        ...(auth && accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: formData ?? (body === undefined ? undefined : JSON.stringify(body)),
    });

  let res = await doFetch();
  if (res.status === 401 && auth && refreshToken && (await tryRefresh())) {
    res = await doFetch();
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) {
        detail = String(data.detail[0].msg);
      }
    } catch {
      // keep default detail
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function login(email: string, password: string): Promise<void> {
  const pair = await api<TokenPair>("/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
  await storeTokens(pair);
}

export async function redeemInvite(token: string, password: string): Promise<void> {
  const pair = await api<TokenPair>("/auth/accept-invite", {
    method: "POST",
    body: { token, password },
    auth: false,
  });
  await storeTokens(pair);
}

export async function logout(): Promise<void> {
  const token = refreshToken;
  await clearAuth();
  if (token) {
    // Best effort — revoking server-side may fail offline; tokens are gone
    // locally either way and the refresh token expires server-side.
    try {
      await api("/auth/logout", { method: "POST", body: { refresh_token: token }, auth: false });
    } catch {
      // ignore
    }
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}
